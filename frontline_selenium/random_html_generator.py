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
            attributes = f"src='{fake.image_url()}' alt='{fake.word()}'"
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