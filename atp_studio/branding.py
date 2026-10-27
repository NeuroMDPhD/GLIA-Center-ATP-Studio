"""Application creator and support details, separate from analysis-engine credits."""

APP_NAME = 'GLIA Center ATP Studio'
CREATOR = 'Seunghwan Choi'
CONTACT_EMAIL = 'medic@khu.ac.kr'

def creator_html():
    return (f'<p>Creator<br>{CREATOR}<br>'
            f'<a style="color:#007bc1" href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>')
