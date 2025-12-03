import requests
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
# from logging_config import logger
# from content import html6
import os




def post_to_wp(html_content, featured_img_url, page_title, brand_name, key_phrase, description, social_image, WP_URL, USERNAME, APP_PASSWORD):
    """Create a new WordPress post using REST API."""

    try:
                            
        # Content to post (HTML)
        soup = BeautifulSoup(html_content, "html.parser")
        first_p = soup.find("p").get_text(" ", strip=True)

        # additional_description = first_p[:85]

        additional_description = first_p[:100]
        
        last_space = additional_description.rfind(" ")  # Find the last space before the cutoff

        if last_space != -1:
            additional_description = additional_description[:last_space]

        full_description = f"{description} {additional_description}"

        # Prepend featured image to content
        page_content = f'<img src="{featured_img_url}" alt="Featured Image" style="width:100%; height:auto;"/>\n' + html_content

        page_data = {
            "title": page_title,
            "content": page_content,
            "status": "publish",
            # "featured_media": 9,  Id of the featured image in WordPress media library
            "meta": {
                "_yoast_wpseo_focuskw": f"{key_phrase}",
                "_yoast_wpseo_title": f"{page_title} | {brand_name}",
                "_yoast_wpseo_metadesc": f"{full_description}",
                "_yoast_wpseo_opengraph-image": social_image,
                "_yoast_wpseo_opengraph-title": f"{page_title} | {brand_name}",
                "_yoast_wpseo_opengraph-description": f"{full_description}",
                "_yoast_wpseo_twitter-image": social_image,
                "_yoast_wpseo_twitter-title": f"{page_title} | {brand_name}",
                "_yoast_wpseo_twitter-description": f"{full_description}"
            }
        }

        response = requests.post(
            WP_URL,
            auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
            json=page_data,
            timeout=30
        )

        return response
    
    # except requests.exceptions.Timeout:
    #     logger.error(f"⏰ Timeout while posting '{page_title}' to WordPress.")
    # except requests.exceptions.RequestException as re:
    #     logger.error(f"🌐 Request error during post_to_wp for '{page_title}': {re}")
    except Exception as e:
        # logger.error(f"❌ Unexpected error in post_to_wp: {e}")
        print("❌ Unexpected error in post_to_wp: {e}")

    return None


# print(post_to_wp(html_content, featured_img_url, page_title, brand_name, key_phrase, description, social_image, WP_URL, USERNAME, APP_PASSWORD))