import base64
import mimetypes
import os.path
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def create_message(sender, to, subject, message_text, attachment=None, cc=""):
    message = MIMEMultipart("mixed")
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    if type(cc) == str and cc != "":
        message["cc"] = cc

    msg_text = MIMEText(message_text, "html")
    message.attach(msg_text)
    if attachment is None:
        raw_message = base64.urlsafe_b64encode(message.as_string()
                                               .encode("utf-8"))
        return {"raw": raw_message.decode("utf-8")}

    content_type, encoding = mimetypes.guess_type(attachment)

    main_type, sub_type = content_type.split("/", 1)
    fp = open(attachment, "rb")
    print(main_type, sub_type)
    msg = MIMEBase(main_type, sub_type)
    msg.set_payload(fp.read())
    encoders.encode_base64(msg)
    fp.close()
    filename = os.path.basename(attachment)
    msg.add_header("Content-Disposition", "attachment", filename=filename)
    message.attach(msg)

    raw_message = base64.urlsafe_b64encode(message.as_string().encode("utf-8"))
    return {"raw": raw_message.decode("utf-8")}


def send_message(service, user_id, message):
    try:
        message = (
            service.users().messages().send(userId=user_id,
                                            body=message).execute()
        )
        print("Message Id: %s" % message["id"])
        return message
    except Exception as e:
        print("An error occurred: %s" % e)
        return None


def send(service, to, subject, message_text, attachment=None, cc=""):
    message = create_message("me", to, subject, message_text, attachment, cc)
    return send_message(service, "me", message)
