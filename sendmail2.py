import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def sendmail(_from, to, subject, html, text):
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = _from
    msg['To'] = to
    
    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')
    
    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)
    
    # Send the message via local SMTP server.
    s = smtplib.SMTP('content-analysis.org', 587, 'amcat.fsw.vu.nl')
    s.login('helpdesk@contentanalysis.nl','knzhrm!!')
    
    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    s.sendmail(_from, to, msg.as_string())
    s.quit()