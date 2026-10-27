"""Application creator and support details, separate from analysis-engine credits."""

APP_NAME = 'ATP ROA Studio'
CREATOR = 'Seunghwan Choi, MD, PhD'
CONTACT_EMAIL = 'medic@khu.ac.kr'

def creator_html():
    return (f'<p><b>Creator / 制作者:</b> {CREATOR}<br>'
            f'<b>Contact / お問い合わせ:</b> '
            f'<a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>')
