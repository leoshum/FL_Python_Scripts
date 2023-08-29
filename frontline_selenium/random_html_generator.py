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
    
    @staticmethod
    def get_random_bull_image_link():
        bull_links = [
            ("https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Taureau_charolais_au_pr%C3%A9.jpg/220px-Taureau_charolais_au_pr%C3%A9.jpg", "220", "165"),
            ("https://content.api.news/v3/images/bin/6d6c1e6d7d30d6a0d0c7b7eca93d09d2", "316", "421"),
            ("https://d266chgl8kxb39.cloudfront.net/image/708002200750/image_bal3f0ud7h1dd49j9iocorbn63/-S480x456-FJPG", "480", "339"),
            ("https://upload.wikimedia.org/wikipedia/commons/b/b5/A_Friesian_Bull%2C_Llandeilo_Graban_-_geograph.org.uk_-_579885.jpg", "640", "426"),
            ("https://www.livetradingnews.com/wp-content/uploads/2021/11/MW-GK927_bull_b_ZQ_20180614134501.jpg", "660", "371"),
            ("https://www.nps.gov/thro/learn/nature/images/Longhorn_2.jpg?maxwidth=1300&maxheight=1300&autorotate=false", "285", "192"),
            ("https://ocj.com/wp-content/uploads/2012/11/Clear-Win-Bull.png", "492", "312"),
            ("https://www.alh-genetics.nl/wp-content/uploads/2021/07/Texas-Longhorn-ALH-embryo.jpg", "560", "375"),
            ("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSLLkJDATA6HT42CkDSeIB8osBmXs35S8ErlCD9kMkxuOx59MtcYnueh-3SxXbHLJFv6Vc&usqp=CAU", "266", "189"),
            ("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQZ_N--Tr3TnFsGQdvWtK6CKf37-IFCmpuVbCPf0y-ID40qmIOKylUxQ0NKPTIfq7AwUZY&usqp=CAU", "261", "193"),
            ("https://media.istockphoto.com/id/488852113/photo/ox-fight.jpg?s=612x612&w=0&k=20&c=3AGRVORHflJTEtzZuFej0W84yr8ETnfoweMB4CbT9Xs=", "612", "408"),
            ("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQCXZVpFS8mIP-9kJ33FHmHv_IPqjbCYY0eQZdbI4bunzrlyAMwv3iz-9W5Xr70lrm1sEw&usqp=CAU", "275", "183"),
            ("https://ichef.bbci.co.uk/news/976/cpsprodpb/166FE/production/_124720919_8a1a0305-094e-416f-883a-d03818e4dcca.jpg", "976", "589"),
            ("https://ichef.bbci.co.uk/news/976/cpsprodpb/D7C0/production/_124723255_cow.jpg", "976", "549"),
            ("https://www.simmental.co.nz/wp-content/uploads/2021/04/Simmental-NZ-Blog_Bull.png", "500", "500"),
            ("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTlXYpwwxboIGHx1tjIeGNoA_7wmQEX1Gj3Jw&usqp=CAU", "300", "168"),
            ("https://alicaforneret.com/wp-content/uploads/2022/12/bull-in-dream.jpg", "900", "600"),
            ("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT78pCkXHjLoenTRiS4Vgb9HlC1bUNRfcRgEg&usqp=CAU", "261", "193"),
            ("https://stmaaprodfwsite.blob.core.windows.net/assets/sites/1/2023/05/200523-Mendel-P-full-height-c-Genus-ABS.jpg", "900", "563"),
            ("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcScGPXo0MxHb8haS0uh3CO0lQjX0pNnDDUVN3UkyrM45Crd7nFVnUrVm7cFo4p8s2R1mYw&usqp=CAU", "275", "183")
        ]
        return random.choice(bull_links)
#def main():
#    dir_path = os.path.abspath(os.path.dirname(__file__)) + "\\bulls\\"
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
#            resized_image.save(f"{dir_path}{filename.split('_')[0]}_{new_width}_{new_height}.jpg", "JPEG", quality=30)
#if __name__ == "__main__":
#    main()