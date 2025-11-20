from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


doc_id = "1J43gRLDYKC8q6EZfQGuOUbarbcDblaF2Jwr-zbpz44M123"
credentials_file = 'doc-reader.json'

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets"
]
creds = service_account.Credentials.from_service_account_file(credentials_file, scopes=SCOPES)

doc_service = build("docs", "v1", credentials=creds)
# sheet_service = build("sheets", "v4", credentials=creds)

requests = [
    {
        "insertText": {
            "location": {"index": 1},
            "text": "Added by Python\n"
        }
    }
]

doc_service.documents().batchUpdate(
    documentId=doc_id,
    body={"requests": requests}
).execute()


