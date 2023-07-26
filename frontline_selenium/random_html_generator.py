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
        dir_path = os.path.abspath(os.path.dirname(__file__)) + "\\cats\\"
        image_id = fake.random_int(min=1, max=21)
        img_path = f"{dir_path}cat_{image_id}.jpg"
        with open(img_path, "rb") as image_file:
            base64_string = base64.b64encode(image_file.read()).decode("utf-8")
        return f"data:image/jpg;base64, {base64_string}"

#def main():
#    dir_path = os.path.abspath(os.path.dirname(__file__)) + "\\cats\\"
#    for filename in os.listdir(dir_path):
#        print(filename)
#        image = Image.open(dir_path + filename)
#        new_width = image.width // 2
#        new_height = image.height // 2
#        resized_image = image.resize((new_width, new_height))
#        resized_image.save(dir_path + filename, "JPEG", quality=70)
#if __name__ == "__main__":
#    main()