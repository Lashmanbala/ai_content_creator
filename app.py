from openai import OpenAI
from dotenv import load_dotenv

# standard environment variable name for OpenAI API key -- OPENAI_API_KEY

load_dotenv()   

client = OpenAI()

response = client.responses.create(
    model="gpt-5-nano",
    input="Write a one-sentence bedtime story about a unicorn."
)

print(response.output_text)