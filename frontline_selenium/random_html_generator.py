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
            ("https://64.media.tumblr.com/4d9b609245367611a3cb9a1d8ae7d863/0b69f974db6053da-71/s640x960/9118708c78749443635e29457bf50edc4476c761.jpg", "640", "775"),
            ("https://images.fineartamerica.com/images/artworkimages/mediumlarge/1/sasquash-bob-christopher.jpg", "596", "900"),
            ("https://i.pinimg.com/236x/9d/be/14/9dbe144bc7ee7e7038e1e2d79cf5b53f.jpg", "236", "314"),
            ("https://i.etsystatic.com/40268241/r/il/f11948/4508558872/il_570xN.4508558872_dvbh.jpg", "570", "570"),
            ("https://i.pinimg.com/236x/13/78/92/137892ca96f2e4b6fa991b80bdaeef4b.jpg", "235", "285"),
            ("https://i.pinimg.com/736x/db/7d/23/db7d23240a7d2f031793618f091dc9ea.jpg", "656", "960"),
            ("https://visitowensboro.com/_uploads/365134714_115168011664735_2048755022115142807_n-768x768.jpg", "768", "768"),
            ("https://images.squarespace-cdn.com/content/v1/5c06dfac4611a0251594ba98/1549332443390-5AJ16TXD44H0BXYDG542/am_edge_sas.jpg?format=1000w", "960", "540"),
            ("https://i.pinimg.com/736x/bc/68/03/bc680373336762610acbba95d855b2f9.jpg", "380", "380"),
            ("https://live.staticflickr.com/65535/52302913020_03d01840d7_b.jpg", "596", "900")
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