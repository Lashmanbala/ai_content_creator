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


tab_id = 't.d5l3v6yhd16t'
def build_requests_from_html(html, starting_index=1, tab_id=tab_id):
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    if body is None:
        body = soup  # fallback

    requests = []
    pending_styles = []
    # Simulating the document's character index while building the requests.
    current_index = starting_index

    # helper to insert text at current_index and increment
    def insert_text_and_advance(text):
        nonlocal current_index, requests
        if not text:
            return (None, None)
        # ensure text uses normalized newlines
        text = text.replace('\r\n', '\n')
        req = {"insertText": {"location": {"tabId": tab_id, "index": current_index}, "text": text}}
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
        pending_styles.append({
            "updateTextStyle": {
                "range": {"startIndex": start, "endIndex": end, "tabId": tab_id},
                "textStyle": style_dict,
                "fields": fields
            }
        })

    def add_paragraph_style(start, end, named_style):
        if start is None or end is None or start == end:
            return
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end, "tabId": tab_id},
                "paragraphStyle": {"namedStyleType": named_style},
                "fields": "namedStyleType"
            }
        })

    def maybe_add_space():
        # Insert a space only if the previous character is not a space or newline
        nonlocal current_index, requests
        if current_index > 1:
            requests.append({
                "insertText": {
                    "location": {"tabId": tab_id, "index": current_index},
                    "text": " "
                }
            })
            current_index += 1

    # Walk direct children of body to keep structure order
    for node in body.children:
        if isinstance(node, str):
            text = clean_text(node)
            if text:
                insert_text_and_advance(text + "\n")
            continue

        name = getattr(node, "name", "").lower()

        if name in ("h1", "h2", "h3", "h4"):
            text = clean_text(node.get_text())
            if not text:
                continue
            # Insert text + newline
            start, end = insert_text_and_advance(text + "\n")

            # apply bold ONLY to visible characters
            add_text_style(start, start + len(text), {"bold": True})

            # Map to named styles
            if name == "h1":
                add_paragraph_style(start, end, "HEADING_1")
            elif name == "h2":
                add_paragraph_style(start, end, "HEADING_2")
            elif name == "h3":
                add_paragraph_style(start, end, "HEADING_3")
            elif name == "h4":
                add_paragraph_style(start, end, "HEADING_4")
        
            
        elif name == "p":
            paragraph_start = current_index

            prev_was_text = False  # track continuity

            for child in node.children:
                cname = getattr(child, "name", None)

                if cname == "strong":
                    t = clean_text(child.get_text())
                    if t:
                        # Insert space when toggling from plain → strong
                        if prev_was_text:
                            maybe_add_space()

                        s, e = insert_text_and_advance(t)
                        add_text_style(s, e, {"bold": True})
                        prev_was_text = True

                elif cname == "a":
                    t = clean_text(child.get_text())
                    href = child.get("href")
                    if t:
                        if prev_was_text:
                            maybe_add_space()

                        s, e = insert_text_and_advance(t)
                        if href:
                            add_text_style(s, e, {"link": {"url": href}})
                        prev_was_text = True

                else:
                    plain = child if isinstance(child, str) else child.get_text()
                    plain = clean_text(plain)
                    if plain:
                        if prev_was_text:
                            maybe_add_space()
                        insert_text_and_advance(plain)
                        prev_was_text = True

            _ , paragraph_end = insert_text_and_advance("\n")

            add_paragraph_style(paragraph_start, paragraph_end, "NORMAL_TEXT")


        elif name == "ul":
            first_item_index = None
            last_item_index = None

            for li in node.find_all("li", recursive=False):
                li_start = current_index

                # Process children inside <li> just like <p> logic
                for child in li.children:
                    prev_was_text = False  # track continuity

                    cname = getattr(child, "name", None)

                    if cname == "strong":
                        t = clean_text(child.get_text())
                        if t:
                            if prev_was_text:
                                maybe_add_space()

                            s, e = insert_text_and_advance(t)
                            add_text_style(s, e, {"bold": True})

                            prev_was_text = True

                    elif cname == "a":
                        t = clean_text(child.get_text())
                        href = child.get("href")
                        if t:
                            if prev_was_text:
                                maybe_add_space()

                            s, e = insert_text_and_advance(t)
                            if href:
                                add_text_style(s, e, {"link": {"url": href}})

                            prev_was_text = True

                    else:
                        # plain text
                        plain = child if isinstance(child, str) else child.get_text()
                        plain = clean_text(plain)
                        if prev_was_text:
                            maybe_add_space()
                        s, e = insert_text_and_advance(plain)
                        add_paragraph_style(s, e, "NORMAL_TEXT")
                        prev_was_text = True

                # End of LI → add newline
                li_end = insert_text_and_advance("\n")[1]

                # Track bullet range
                if first_item_index is None:
                    first_item_index = li_start
                last_item_index = li_end

            # Apply bullets to the whole UL
            if first_item_index is not None:
                requests.append({
                    "createParagraphBullets": {
                        "range": {"startIndex": first_item_index, "endIndex": last_item_index, "tabId": tab_id},
                        "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
                    }
                })


        elif name == "ol":
            first_item_index = None
            last_item_index = None

            for li in node.find_all("li", recursive=False):
                li_start = current_index

                # Process children inside <li> just like <p> logic
                for child in li.children:
                    prev_was_text = False  # track continuity

                    cname = getattr(child, "name", None)

                    if cname == "strong":
                        t = clean_text(child.get_text())
                        if t:
                            if prev_was_text:
                                maybe_add_space()

                            s, e = insert_text_and_advance(t)
                            add_text_style(s, e, {"bold": True})
                            requests.append({
                                    "insertText": {
                                        "location": {"tabId": tab_id, "index": current_index},
                                        "text": " "
                                    }
                                })
                            current_index += 1

                            prev_was_text = True

                    elif cname == "a":
                        t = clean_text(child.get_text())
                        href = child.get("href")
                        if t:
                            if prev_was_text:
                                maybe_add_space()

                            s, e = insert_text_and_advance(t)
                            if href:
                                add_text_style(s, e, {"link": {"url": href}})

                            prev_was_text = True

                    else:
                        # plain text
                        plain = child if isinstance(child, str) else child.get_text()
                        plain = clean_text(plain)
                        if prev_was_text:
                            maybe_add_space()
                        s, e = insert_text_and_advance(plain)
                        add_paragraph_style(s, e, "NORMAL_TEXT")
                        prev_was_text = True

                # End of LI → add newline
                li_end = insert_text_and_advance("\n")[1]

                # Track bullet range
                if first_item_index is None:
                    first_item_index = li_start
                last_item_index = li_end

            # Apply bullets to the whole UL
            if first_item_index is not None:
                requests.append({
                    "createParagraphBullets": {
                        "range": {"startIndex": first_item_index, "endIndex": last_item_index, "tabId": tab_id},
                        "bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN"
                    }
                })

            requests.extend(pending_styles)
            pending_styles = []

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
    # print("Response summary keys:", list(res.keys()))
    print("Open the doc in Google Drive to review formatting.")



if __name__ == "__main__":
    main()
