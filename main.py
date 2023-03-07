#!/usr/bin/env python3

import argparse
import base64
import datetime
import re

from bs4 import BeautifulSoup
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from jinja2 import Template
from tqdm import tqdm

USER_ID = "me"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
MAX_RESULTS = 500


def extract_unsubscribe_info_from_header(header_value):
    if header_value is None:
        return "", ""

    urls = re.findall(r"<(https?://\S+)>", header_value)
    emails = re.findall(r"<(\S+@\S+)>", header_value)
    url = ""
    email = ""
    if len(urls) > 0:
        url = urls[0]
    if len(emails) > 0:
        email = emails[0]
    return url, email


stats = {
    'link': 0,
    'href': 0,
    'child': 0,
    'last_chance_parent': 0,
    'last_chance_sibling': 0,
    'last_chance_family': 0,

}


def extract_unsubscribe_link(email_body):
    soup = BeautifulSoup(email_body, "html.parser")
    for link in soup.find_all("a", string=re.compile(r"unsubscribe", re.IGNORECASE)):
        stats['link'] += 1
        return link.get("href")
    for link in soup.find_all("a", href=re.compile(r"unsubscribe", re.IGNORECASE)):
        stats['href'] += 1
        return link.get("href")
    for el in soup.find_all(True, string=re.compile(r"unsubscribe", re.IGNORECASE)):
        link = el.find_parent("a")
        if link:
            stats['child'] += 1
            return link.get("href")
    """
        <p><span><a href="https://...">CLICK HERE</a></span> TO UNSUBSCRIBE</p>
        It fails because tag.find_all()) != 0 and doesn't find the element. Didn't find better solution
        But I wont invest time since is very little number of emails in my set.
    """
    last_chance = soup.find_all(
        lambda tag: re.search("unsubscribe", tag.text, re.IGNORECASE)
    )
    if len(last_chance) > 0:
        last_chance = last_chance[-1]
        link = last_chance.find_parent("a")
        if link:
            stats['last_chance_parent'] += 1
            return link.get("href")
        link = last_chance.find("a")
        if link:
            stats['last_chance_sibling'] += 1
            return link.get("href")
        link = last_chance.parent.find("a")
        if link:
            stats['last_chance_family'] += 1
            return link.get("href")
    return ""


def extract_name_and_email(sender):
    pattern = r"^(.*) <(.*)>$"  # regular expression pattern to match the format

    match = re.match(pattern, sender)  # try to match the pattern in the given text
    if match:
        name = match.group(1)  # get the first group (text) from the match
        email = match.group(2)  # get the second group (email) from the match
        return email, name
    else:
        return "", sender


def render_template(context, filename):
    with open("template.html", "r") as f:
        template_str = f.read()
    template = Template(template_str)

    html_table = template.render(context=context)
    with open(filename, "w") as f:
        f.write(html_table)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--before",
        help="before this time the emails wont be contemplated. MM/DD/YY",
        required=False,
    )
    parser.add_argument(
        "--after", help="after this time the emails wont be contemplated. MM/DD/YY", required=True
    )
    parser.add_argument(
        "--credentials",
        help='path to the credentials.json check "https://developers.google.com/gmail/api/quickstart/python"',
        required=True,
    )
    parser.add_argument(
        "--output",
        help='where the html file should be generated',
        required=True,
    )
    parser.add_argument(
        "--extra-search-param",
        help='add extra string to narrow down the search: example "NOT label:inbox"',
        required=False,
    )

    args = parser.parse_args()

    return args.credentials, args.output, args.before, args.after, args.extra_search_param


def main():
    (credentials, output_file, before, after, extra_search_param) = parse_args()

    flow = InstalledAppFlow.from_client_secrets_file(credentials, SCOPES)
    credentials = flow.run_local_server(port=0)

    service = build("gmail", "v1", credentials=credentials)

    email_data = {}
    messages = []

    next_page_token = None
    while True:
        print("Checking for mails for another %s messages" % MAX_RESULTS)
        search_string = (
            "unsubscribe after:%s before:%s" % (after, before)
            if before
            else "unsubscribe after:%s" % after
        )
        if extra_search_param:
            search_string += ' (%s)' % extra_search_param
        results = (
            service.users()
            .messages()
            .list(
                userId=USER_ID,
                q=search_string,
                maxResults=MAX_RESULTS,
                pageToken=next_page_token,
            )
            .execute()
        )
        messages.extend(results.get("messages", []))
        next_page_token = results.get("nextPageToken")
        if not next_page_token:
            break

    if len(messages) == 0:
        print("Nothing to show")
        exit()

    print("We found %s mails" % (len(messages)))

    for message in tqdm(messages):
        msg = (
            service.users()
            .messages()
            .get(userId=USER_ID, id=message["id"], format="full")
            .execute()
        )
        payload = msg["payload"]
        headers = payload["headers"]

        email_title = ""
        sender_email = ""
        sender_name = ""
        unsubscribe_link = ""
        unsubscribe_email = ""
        last_email_date = datetime.datetime.fromtimestamp(
            int(msg["internalDate"]) / 1000
        ).date()

        for header in headers:
            if header["name"] == "List-Unsubscribe":
                (
                    unsubscribe_link,
                    unsubscribe_email,
                ) = extract_unsubscribe_info_from_header(header["value"])
            if header["name"] == "Subject":
                email_title = header["value"]
            elif header["name"] == "From":
                (sender_email, sender_name) = extract_name_and_email(header["value"])

        if unsubscribe_link == "":
            body_message = ""
            parts = payload.get("parts")
            if parts:
                for part in parts:
                    body = part.get("body")
                    data = body.get("data")
                    mime_type = part.get("mimeType")

                    if mime_type == "multipart/alternative":
                        sub_parts = part.get("parts")
                        for p in sub_parts:
                            sub_mime_type = p.get("mimeType")
                            if sub_mime_type == "text/html":
                                data = p.get("body").get("data")
                                body_message = base64.urlsafe_b64decode(data)
                                break
                    if mime_type == "multipart/related":
                        sub_parts = part.get("parts")
                        for p in sub_parts:
                            body = p.get("body")
                            data = body.get("data")
                            mime_type = p.get("mimeType")
                            # let's exclude this case since we use soap
                            # if mimeType == 'text/plain':
                            #     body_message = base64.urlsafe_b64decode(data)
                            if mime_type == "text/html":
                                body_message = base64.urlsafe_b64decode(data)
                    # let's exclude this case since we use soap
                    # elif mimeType == 'text/plain':
                    #     body_message = base64.urlsafe_b64decode(data)
                    elif mime_type == "text/html":
                        body_message = base64.urlsafe_b64decode(data)

            if not body_message and "body" in payload and "data" in payload["body"]:
                body_message = base64.urlsafe_b64decode(payload["body"]["data"])

            unsubscribe_link = extract_unsubscribe_link(
                body_message
                if isinstance(body_message, str)
                else body_message.decode("UTF8")
            )

        if sender_email not in email_data:
            email_data[sender_email] = {
                "sender_email": sender_email,
                "sender_name": sender_name,
                "id": message["id"],
                "title": email_title,
                "last_email_date": last_email_date,
                "unsubscribe_link": unsubscribe_link,
                "unsubscribe_email": unsubscribe_email,
                "count": 1,
            }
        else:
            email_data[sender_email]["count"] += 1
            if last_email_date > email_data[sender_email]["last_email_date"]:
                email_data[sender_email]["id"]: message["id"]
                email_data[sender_email]["sender_name"]: message[
                    "sender_name"
                ]  # some place like LinkedIn change this
                email_data[sender_email]["title"] = email_title
                email_data[sender_email]["last_email_date"] = last_email_date
                email_data[sender_email]["unsubscribe_link"] = unsubscribe_link
                email_data[sender_email]["unsubscribe_email"] = unsubscribe_email
                email_data[sender_email]["google_search"] = sender_email

    render_template(
        {"groups": list(email_data.values()), "total_messages": len(messages)},
        output_file,
    )

    print(stats)


if __name__ == "__main__":
    main()
