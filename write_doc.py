from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
import re
from content import html, mdc


SERVICE_ACCOUNT_FILE = "doc-reader.json"
SCOPES = ["https://www.googleapis.com/auth/documents"]


def auth_docs():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build("docs", "v1", credentials=creds)
    return service


def clean_text(s):
    # normalize whitespace
    return re.sub(r'\s+', ' ', s).strip()


def build_requests_from_html(html, starting_index=1):
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    if body is None:
        body = soup  # fallback

    requests = []
    # Simulating the document's character index while building the requests.
    current_index = starting_index

    # helper to insert text at current_index and increment
    def insert_text_and_advance(text):
        nonlocal current_index, requests
        if not text:
            return (None, None)
        # ensure text uses normalized newlines
        text = text.replace('\r\n', '\n')
        req = {"insertText": {"location": {"index": current_index}, "text": text}}
        requests.append(req)
        start = current_index
        current_index += len(text)
        end = current_index
        return start, end

    # collecting style requests as we go (they depend on start/end indices we've just recorded)
    def add_text_style(start, end, style_dict):
        # fields is comma-separated keys of style_dict
        if start is None or end is None or start == end:
            return
        
        fields = ",".join(style_dict.keys())
        requests.append({
            "updateTextStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "textStyle": style_dict,
                "fields": fields
            }
        })

    def add_paragraph_style(start, end, named_style):
        if start is None or end is None or start == end:
            return
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "paragraphStyle": {"namedStyleType": named_style},
                "fields": "namedStyleType"
            }
        })

    # Walk direct children of body to keep structure order
    for node in body.children:
        if isinstance(node, str):
            text = clean_text(node)
            if text:
                insert_text_and_advance(text + "\n")
            continue

        name = getattr(node, "name", "").lower()

        if name in ("h1", "h2", "h3"):
            text = clean_text(node.get_text())
            if not text:
                continue
            # Insert text + newline
            start, end = insert_text_and_advance(text + "\n")

            add_text_style(start, end, {"bold": True})

            # Map to named styles
            if name == "h1":
                add_paragraph_style(start, end, "HEADING_1")
            elif name == "h2":
                add_paragraph_style(start, end, "HEADING_2")
            elif name == "h3":
                add_paragraph_style(start, end, "HEADING_3")

        elif name == "p":
            paragraph_start = current_index
            # iterate over children to capture inline styles
            for child in node.children:
                if getattr(child, "name", None) == "strong":
                    t = clean_text(child.get_text())
                    # t = child.get_text()
                    if t:
                        s, e = insert_text_and_advance(t)
                        add_text_style(s, e, {"bold": True})

                elif getattr(child, "name", None) == "a":
                    t = clean_text(child.get_text())
                    href = child.get("href")
                    if t:
                        s, e = insert_text_and_advance(t)
                        if href:
                            add_text_style(s, e, {"link": {"url": href}})
                            # insert_text_and_advance("\u200b")
                else:
                    # plain text node (including text inside other non-styled tags)
                    plain = ""
                    if isinstance(child, str):
                        plain = child
                    else:
                        plain = child.get_text()
                    plain = clean_text(plain)
                    if plain:
                        insert_text_and_advance(plain)
            # end paragraph - add newline
            insert_text_and_advance("\n")

        elif name == "ul":
            # for ul: insert each <li> as a new line, then call createParagraphBullets on that range
            first_item_index = None
            last_item_index = None
            li_count = 0
            for li in node.find_all("li", recursive=False):
                li_text = clean_text(li.get_text())
                if not li_text:
                    continue
                li_count += 1
                s, e = insert_text_and_advance(li_text + "\n")
                if first_item_index is None:
                    first_item_index = s
                last_item_index = e
            # if li_count > 0:
            #     # create bullets for the range
            #     requests.append({
            #                 "createParagraphBullets": {
            #                     "range": {"startIndex": s, "endIndex": e}
            #                 }
            #             })


        elif name == "ol":
            # similar to ul but we can use the same bullets and let Google handle numbering via named styles
            first_item_index = None
            last_item_index = None
            li_count = 0
            for li in node.find_all("li", recursive=False):
                li_text = clean_text(li.get_text())
                if not li_text:
                    continue
                li_count += 1
                s, e = insert_text_and_advance(li_text + "\n")
                if first_item_index is None:
                    first_item_index = s
                last_item_index = e
            if li_count > 0:
                # create numbered bullets
                requests.append({
                    "createParagraphBullets": {
                        "range": {"startIndex": first_item_index, "endIndex": last_item_index},
                        "bulletPreset": "NUMBERED_DECIMAL"
                    }
                })

        else:
            # fallback: insert the text content and a newline
            txt = clean_text(node.get_text() or "")
            if txt:
                insert_text_and_advance(txt + "\n")

    return requests


def main():
    docs_service = auth_docs()
    # Create a new Google Doc
    # doc = docs_service.documents().create(body={"title": DOCUMENT_TITLE}).execute()
    doc_id = '1J43gRLDYKC8q6EZfQGuOUbarbcDblaF2Jwr-zbpz44M'
    # print("Created document:", doc_id)

    # build requests
    requests = build_requests_from_html(html)

    if not requests:
        print("No requests generated.")
        return

    # Send batchUpdate
    batch = {"requests": requests}
    res = docs_service.documents().batchUpdate(documentId=doc_id, body=batch).execute()
    print("Batch update executed.")
    print("Response summary keys:", list(res.keys()))
    print("Open the doc in Google Drive to review formatting.")

if __name__ == "__main__":
    main()
