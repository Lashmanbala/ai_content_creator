from openai import OpenAI
from dotenv import load_dotenv
from prompt import prompt, sys_msg
from write_doc import auth_docs, build_requests_from_html
import os
import time
from post import post_to_wp

# standard environment variable name for OpenAI API key -- OPENAI_API_KEY

load_dotenv()   

client = OpenAI()

API_KEY_ENV_VAR = "OPENAI_API_KEY"  
MODEL = "gpt-4.1-nano"
OUTPUT_DIR = "."
MAX_TOKENS = 2500
# max_completion_tokens = 2500

# USERNAME = os.getenv("WP_USERNAME")
# APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
# WP_URL = os.getenv("WP_URL")
# featured_img_url = os.getenv("FEATURED_IMAGE_URL")
# social_image = os.getenv("SOCIAL_IMAGE_URL")
# country_name = os.getenv("COUNTRY_NAME")
# category_name = os.getenv("CATEGORY_NAME")
# page_title = os.getenv("page_title_format")
# key_phrase = os.getenv("key_phrase_format")
# description = os.getenv("description_format")
# brand_name = os.getenv("BRAND_NAME")
# print(WP_URL)

'''
docs_service = auth_docs()
doc_id = '1J43gRLDYKC8q6EZfQGuOUbarbcDblaF2Jwr-zbpz44M'

doc = docs_service.documents().get(documentId=doc_id, includeTabsContent=True).execute()

tabs = doc.get("tabs", [])
print("Tabs in document:", [tab["tabProperties"]["title"] for tab in tabs])

if not tabs:
    raise Exception("No tabs found in the document")
tab_dict = {}
for t in tabs:
    tab_title = t["tabProperties"]["title"]
    tab_id = t["tabProperties"]["tabId"]
    
    if not tab_title in tab_dict.keys():
        tab_dict[tab_title] = tab_id

    # print("Tab title:", t["tabProperties"]["title"], "ID:", t["tabProperties"]["tabId"])
print(tab_dict)


cities = [tab["tabProperties"]["title"] for tab in tabs] '''
# city_name = "Mumbai"

cities = ["Chennai"]

prompt_template = prompt

for city_name in cities:
    s_time = time.time()
    print(f"\n=== Generating content for city: {city_name} ===\n")
    time.sleep(10)
    country_name = "India"
    # prompt = build_prompt(city)
    filename_safe = city_name.lower().replace(" ", "_")
    output_path = os.path.join(OUTPUT_DIR, f"{filename_safe}_seo_page3.txt")

    # Basic retry/backoff in case of transient failures
    max_retries = 1
    backoff = 5.0

    final_prompt = prompt_template.format(city_name=city_name, country_name=country_name)
     
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[Attempt {attempt}] Calling model to generate content for {city_name}...")
            time.sleep(40)
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": final_prompt}
                ],
                max_tokens=MAX_TOKENS,
                # max_completion_tokens=MAX_TOKENS
                temperature=0.5  
            )
            
            choices = response.choices or []  # Extract content

            if not choices:
                raise RuntimeError("API returned no choices; retrying.")

            content = choices[0].message.content
            # Basic validation: ensure we have at least 5000 characters 
            if not content  or len(content) < 5000:
                print("Warning: generated content seems short; retrying once.")
                raise RuntimeError("Generated content too short.")
            else:
                print('----Content generated----')
                e_time = time.time()
                # print(e_time - s_time)
                usage = response.usage or {}
                print(f'Usage: {usage}')
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
                print('++++written to file++++')
                time.sleep(10)
            
            # tab_id = tab_dict[city_name]
            # requests = build_requests_from_html(content, tab_id=tab_id)
 
            # if not requests:
            #     print("No requests generated.")
            #     return

            # Send batchUpdate
            # batch = {"requests": requests}
            # docs_service.documents().batchUpdate(documentId=doc_id, body=batch).execute()

            # print("Batch update executed.")
            # print(f"Open the doc tab {city_name} with id : {tab_id} in Google Drive to review formatting.")
            # time.sleep(10)

            # print(f"✅ Generated content saved to: {output_path}")

            # response = post_to_wp(content, featured_img_url, page_title, brand_name, key_phrase, description, social_image, WP_URL, USERNAME, APP_PASSWORD)
            # print(f"✅ Generated content posted to WordPress for city: {city_name}")
            # if response.status_code == 201:
            #     page_url = response.json().get("link", "")
            #     print(f"✅ Created page for '{city_name}': {page_url}")

        except Exception as e:
            print(f"Error on attempt {attempt}: {e}")
            if attempt == max_retries:
                raise
            else:
                time.sleep(backoff * attempt)