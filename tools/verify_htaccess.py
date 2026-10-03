"""Run the approved temporary file-denial check, preserving all site data."""

import argparse
from ftplib import FTP_TLS, error_perm
from io import BytesIO
import os
import ssl
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


RULE = b'<Files ".ftp-deploy-sync-state.json">\n    Require all denied\n</Files>\n'
SITE = "https://lincolndevotional.com"
PAGES = ["/", "/explore/", "/entries/january-1/"]
STATE = "/.ftp-deploy-sync-state.json"
CACHE = "/data/entry_topics_cache.json"


def check_http(path, expected):
    request = Request(
        f"{SITE}{path}?htaccess-check={time.time_ns()}",
        headers={"Cache-Control": "no-cache"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            status = response.status
    except HTTPError as error:
        status = error.code
        error.close()
    print(f"GET {path}: {status} (expected {expected})", flush=True)
    if status != expected:
        raise RuntimeError(f"Unexpected HTTP status for {path}")


def read_htaccess(ftp):
    contents = BytesIO()
    try:
        ftp.retrbinary("RETR .htaccess", contents.write)
    except error_perm as error:
        if not str(error).startswith("550"):
            raise
        # A failed RETR alone cannot establish absence; verify the listing too.
        names = {name for name, _ in ftp.mlsd()}
        if ".htaccess" in names:
            raise RuntimeError("Existing .htaccess cannot be read; leaving it untouched")
        return None
    return contents.getvalue()


def remove_test_rule(ftp):
    contents = read_htaccess(ftp)
    if contents is None:
        print("No temporary .htaccess remains", flush=True)
        return
    if contents != RULE:
        raise RuntimeError("Unexpected .htaccess contents; leaving it untouched")
    ftp.delete(".htaccess")
    if read_htaccess(ftp) is not None:
        raise RuntimeError("Temporary .htaccess was not removed")
    print("Removed temporary .htaccess; absence verified", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()

    with FTP_TLS(context=ssl.create_default_context(), timeout=20) as ftp:
        ftp.connect(os.environ["FTP_SERVER"], 21)
        ftp.login(os.environ["FTP_USERNAME"], os.environ["FTP_PASSWORD"])
        ftp.prot_p()
        ftp.cwd(os.environ["FTP_SERVER_DIR"])
        if args.cleanup:
            remove_test_rule(ftp)
        else:
            if read_htaccess(ftp) is not None:
                raise RuntimeError("Root .htaccess already exists; no files changed")
            names = {name for name, _ in ftp.mlsd()}
            if ".ftp-deploy-sync-state.json" not in names:
                raise RuntimeError("Deploy state absent; check FTP document root")
            print("FTPS root verified; root .htaccess is absent", flush=True)
            for path in PAGES + [STATE, CACHE]:
                check_http(path, 200)
            try:
                ftp.storbinary("STOR .htaccess", BytesIO(RULE))
                if read_htaccess(ftp) != RULE:
                    raise RuntimeError("Uploaded rule does not match")
                print("Installed only the approved temporary deny rule", flush=True)
                check_http(STATE, 403)
                for path in PAGES + [CACHE]:
                    check_http(path, 200)
            finally:
                remove_test_rule(ftp)
        for path in PAGES + [STATE, CACHE]:
            check_http(path, 200)
        print("Site responses restored; JSON files preserved", flush=True)


if __name__ == "__main__":
    main()
