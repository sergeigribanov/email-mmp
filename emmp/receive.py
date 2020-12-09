import base64
import os
import re


def download_attachments(service, message, prefix, result):
    if "parts" not in message["payload"]:
        return

    mid = message["id"]
    for part in message["payload"]["parts"]:
        if "attachmentId" not in part["body"]:
            continue

        aid = part["body"]["attachmentId"]
        if "application" in part["mimeType"] or "image" in part["mimeType"]:
            att = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=mid, id=aid)
                .execute()
            )
            data = base64.urlsafe_b64decode(att["data"].encode("UTF-8"))
            path = os.path.join(prefix, part["filename"])
            with open(path, "wb") as fl:
                fl.write(data)


def process_parts(result, mid, message):
    if "parts" not in message["payload"]:
        return

    for part in message["payload"]["parts"]:
        if part["partId"] == "0" and part["mimeType"] == "text/plain":
            result[mid]["message"] = base64.urlsafe_b64decode(
                part["body"]["data"]
            ).decode("utf-8")

        if part["mimeType"] == "multipart/alternative":
            for subpart in part["parts"]:
                if subpart["mimeType"] == "text/plain":
                    result[mid]["message"] = base64.urlsafe_b64decode(
                        subpart["body"]["data"]
                    ).decode("utf-8")

                elif part["mimeType"] == "text/plain":
                    result[mid]["message"] = base64.urlsafe_b64decode(
                        part["body"]["data"]
                    ).decode("utf-8")


def process_message(result, message):
    mid = message["id"]
    result[mid] = dict()
    result[mid]["threadId"] = message["threadId"]
    result[mid]["snippet"] = message["snippet"]
    for header in message["payload"]["headers"]:
        if header["name"] == "Subject":
            result[mid]["subject"] = header["value"]
        elif header["name"] == "From":
            result[mid]["from"] = header["value"]
        elif header["name"] == "Date":
            result[mid]["date"] = header["value"]

    process_parts(result, mid, message)


def receive(service, query, prefix=None, labels=["INBOX", "SPAM"], attachments=False):
    threads = (
        service.users()
        .threads()
        .list(userId="me", q=query)
        .execute()
        .get("threads", [])
    )
    ids = [el["id"] for el in threads]
    result = dict()
    for tid in ids:
        tdata = service.users().threads().get(userId="me", id=tid).execute()
        for message in tdata["messages"]:
            is_label = any(el in message["labelIds"] for el in labels)
            if is_label:
                process_message(result, message)
                if attachments:
                    mid = message["id"]
                    from_string = result[mid]["from"]
                    q = re.match("(.*)<(.*)>", from_string)
                    if q:
                        att_prefix = os.path.join(prefix, from_string, q.group(2))
                    else:
                        att_prefix = os.path.join(prefix, from_string)

                    if not os.path.exists(att_prefix):
                        os.makedirs(att_prefix)

                    download_attachments(service, message, att_prefix, result)

    return result
