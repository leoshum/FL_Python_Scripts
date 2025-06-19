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
            src, w, h = RandomHtmlGenerator.get_random_bull_image_link()
            attributes = f"src='{src}' alt='{fake.word()}'"
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
        animal_links = [
            ("https://images.unsplash.com/photo-1564349683136-77e08dba1ef7?w=800&h=600&fit=crop", "800", "600"),
            ("https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=900&h=675&fit=crop", "900", "675"),
            ("https://images.unsplash.com/photo-1574870111867-089730e5a72b?w=1200&h=800&fit=crop", "1200", "800"),
            ("https://images.unsplash.com/photo-1551717743-49959800b1f6?w=500&h=600&fit=crop", "500", "600"),
            ("https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1600&h=900&fit=crop", "1600", "900"),
            ("https://images.unsplash.com/photo-1583512603805-3cc6b41f3edb?w=800&h=600&fit=crop", "800", "600"),
            ("https://images.unsplash.com/photo-1551135049-8a33b5883817?w=1280&h=720&fit=crop", "1280", "720"),
            ("https://images.unsplash.com/photo-1546026423-cc4642628d2b?w=1920&h=1080&fit=crop", "1920", "1080")
        ]
        return random.choice(animal_links)
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