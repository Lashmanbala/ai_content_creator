from openai import OpenAI
from dotenv import load_dotenv
from prompt import prompt
import os
import time

# standard environment variable name for OpenAI API key -- OPENAI_API_KEY

load_dotenv()   

client = OpenAI()

API_KEY_ENV_VAR = "OPENAI_API_KEY"  
MODEL = "gpt-4.1-nano"
OUTPUT_DIR = "."
MAX_TOKENS = 2500


cities = ['Mumbai', 'Chennai', 'Bangalore']
# city_name = "Mumbai"

prompt_template = prompt

for city_name in cities:
    country_name = "India"
    # prompt = build_prompt(city)
    filename_safe = city_name.lower().replace(" ", "_")
    output_path = os.path.join(OUTPUT_DIR, f"{filename_safe}_seo_page.html")

    # Basic retry/backoff in case of transient failures
    max_retries = 1
    backoff = 5.0

    final_prompt = prompt_template.format(city_name=city_name, country_name=country_name)
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[Attempt {attempt}] Calling model {MODEL} to generate content for {city_name}...")
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a 20+ years experienced SEO-friendly & user-friendly website content writer and a professional SEO copywriter who must follow formatting and content instructions exactly. Output the content strictly in html format. You are going to write content for multiple cities. Each content must be unique and the structure must be unique."},
                    {"role": "user", "content": final_prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.2  # lower temperature for consistent output
            )

            choices = response.choices or []  # Extract content

            if not choices:
                raise RuntimeError("API returned no choices; retrying.")

            content = choices[0].message.content
            # Basic validation: ensure we have at least 2000 characters 
            if not content or len(content) < 2000:
                print("Warning: generated content seems short; retrying once.")
                raise RuntimeError("Generated content too short.")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            usage = response.usage or {}
            print(f'Usage: {usage}')

            print(f"✅ Generated content saved to: {output_path}")
            

        except Exception as e:
            print(f"Error on attempt {attempt}: {e}")
            if attempt == max_retries:
                raise
            else:
                time.sleep(backoff * attempt)


# {
#     "id": "chatcmpl-abc123",
#     "object": "chat.completion",
#     "created": 1677858242,
#     "model": "gpt-3.5-turbo",
#     "usage": {
#         "prompt_tokens": 13,
#         "completion_tokens": 7,
#         "total_tokens": 20
#     },
#     "choices": [
#         {
#             "message": {
#                 "role": "assistant",
#                 "content": "This is a test!"
#             }
#         }
#     ]
# }
'''
Usage:CompletionUsage(completion_tokens=2218, prompt_tokens=1019, total_tokens=3237, 
  
                    completion_tokens=2057, prompt_tokens=1019, total_tokens=3076, 
                    completion_tokens=2276, prompt_tokens=1019, total_tokens=3295,
                                                                  '''