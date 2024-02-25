import os
import base64
#from PIL import Image
#import io
from faker import Faker
import random

class RandomHtmlGenerator:
    @staticmethod
    def generate_random_html(depth=0):
        if depth > 10:
            return ''
        
        fake = Faker()
        html_tags = ["<h1>", "<h2>", "<h3>", "<p>", "<div>", "<span>", "<img", "<a"]
        html_lists = ["<ul>", "<ol>"]
        random_tag = random.choice(html_tags)

        if random_tag == "<img":
            attributes = f"src='{RandomHtmlGenerator.get_random_image_link()}' alt='{fake.word()}'"
            html = f"{random_tag} {attributes} />"
        elif random_tag == "<a":
            attributes = f"href='{fake.url()}'"
            text = fake.word()
            html = f"{random_tag} {attributes}>{text}</a>"
        else:
            text = fake.sentence()
            html = f"{random_tag}{text}</{random_tag[1:]}"

        if random_tag in ["<ul>", "<ol>"]:
            html += f"{random.choice(html_lists)}"
            list_items = [fake.word() for _ in range(random.randint(3, 6))]
            html += ''.join([f"<li>{item}</li>" for item in list_items])
            html += f"</{random_tag[1:]}"

        for _ in range(random.randint(0, 2)):
            html += RandomHtmlGenerator.generate_random_html(depth + 1)

        return html

    @staticmethod
    def get_random_image_link():
        fake = Faker()
        dir_path = os.path.abspath(os.path.dirname(__file__)) + "\\sasquash\\"
        image_id = fake.random_int(min=1, max=10)
        img_path = f"{dir_path}{image_id}.jpg"
        with open(img_path, "rb") as image_file:
            base64_string = base64.b64encode(image_file.read()).decode("utf-8")
        return f"data:image/jpg;base64, {base64_string}"
    
    @staticmethod
    def get_random_bull_image_link():
        bull_links = [
            ("https://www.krugerpark.co.za/images/1-honey-badger-moswe590a-590x390.jpg", "590", "390"),
            ("hhttps://dehayf5mhw1h7.cloudfront.net/wp-content/uploads/sites/1491/2023/10/25090332/Honey-Badger-1024x534.png", "1024", "534"),
            ("https://i.vimeocdn.com/video/1647376585-fde09ec80f8f2bc412c2bedb290749a0f8034bbb3d6528fb915d27497f76ad6e-d_750x421.875?q=60", "750", "421"),
            ("https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/ffc560e5-0cc9-4d86-8c14-8d001522c0f9/width=450/03050-836191865-buffed,%20bodybuilder,%20%20honey%20badger%20,.jpeg", "450", "450"),
            ("https://cdn1.tedsby.com/tb/large/storage/1/5/7/157196/stuffed-animal-honey-badger-by-yulia-leonovich.jpg", "581", "466"),
            ("https://www.travelbutlers.com/images/450px/1_450_1_dreamstimemaximum_24822528_KALAHARI_SOUTH_AFRICA.jpg", "450", "450"),
            ("https://www.jukani.co.za/storage/media/2023/05/hb.jpg", "504", "662"),
            ("https://www.safarispecialists.net/news/wp-content/uploads/2017/10/Honey-badger-cute-image-2-2.jpg", "960", "540"),
            ("https://www.shadowsofafrica.com/media/catalog/product/cache/4/small_image/500x/040ec09b1e35df139433887a97daa66f/h/o/honey_badger.jpg", "499", "333"),
            ("https://www.activewild.com/wp-content/uploads/2024/02/Honey-Badger-Close-Up-Face.jpg", "900", "600")
        ]
        return random.choice(bull_links)
#def main():
#    dir_path = os.path.abspath(os.path.dirname(__file__)) + "\\sasquash\\"
#    for filename in os.listdir(dir_path):
#        image = Image.open(dir_path + filename)
#        image = image.convert("RGB")
#        new_width = image.width
#        new_height = image.height
#        image_size_kb = os.path.getsize(dir_path + filename) / 1024
#        if image_size_kb >= 13:
#            print(filename)
#            new_width = image.width // 2
#            new_height = image.height // 2
#            resized_image = image.resize((new_width, new_height))
#            resized_image.save(f"{dir_path}{filename}", "JPEG", quality=30)
#if __name__ == "__main__":
#    main()