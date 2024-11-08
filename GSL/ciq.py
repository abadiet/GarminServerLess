import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import webbrowser


class CIQ:
    """
    A class to interact with the Garmin Connect IQ platform.
    """

    @staticmethod
    def get_app_guid(ciq_url: str) -> str:
        """
        Extracts the application GUID from a given CIQ URL.

        Args:
            ciq_url (str): The CIQ URL from which to extract the application GUID.
        Returns:
            guid (str): The extracted application GUID.
        Raises:
            Exception: If the provided CIQ URL is invalid and does not contain an application GUID.
        """

        app_guid = ciq_url.split("/apps/")
        if len(app_guid) < 2:
            raise Exception(f"Invalid CIQ URL: {ciq_url}")
        app_guid = app_guid[1].split("/")[0]
        return app_guid

    @staticmethod
    def get_last_app_version_guid(app_guid: str, session_cookie: str) -> str:
        """
        Retrieves the last version GUID of a Garmin app.

        Args:
            app_guid (str): The GUID of the Garmin app.
            session_cookie (str): The cookie named *session* when logged in to apps.garmin.com. Can be any Garmin account, even a junk one.

        Returns:
            version_guid (str): The last version GUID of the specified Garmin app.

        Raises:
            Exception: If the app version cannot be retrieved.
        """

        resp = requests.post(f"https://apps.garmin.com/api/appsLibraryExternalServices/api/asw/apps/{app_guid}/install?unitId=a", cookies={"session": session_cookie})
        arr = resp.text.split("appVersionId=")
        if len(arr) != 2:
            raise Exception(f"Failed to get app version:\n{resp.text}")
        return arr[1].split(",")[0]
    
    @staticmethod
    def get_app_info(app_guid: str) -> str:
        """
        Fetches the application information from the Garmin Connect IQ Store using the provided app GUID.

        Args:
            app_guid (str): The GUID of the application to fetch information for.

        Returns:
            info (str): The JSON response from the Garmin Connect IQ Store API as a string.

        Raises:
            Exception: If the request to the Garmin Connect IQ Store API fails or if the response cannot be parsed as JSON.
        """

        resp = requests.get(f"https://apps.garmin.com/api/appsLibraryExternalServices/api/asw/apps/{app_guid}")
        if resp.status_code != 200:
            raise Exception(f"Failed to get app version, error {resp.status_code}:\n{resp.text}")
        try:
            resp = resp.json()
        except Exception as e:
            raise Exception(f"Failed to parse the string\n\n{resp.text}\n\n: {e}")
        return resp

    @staticmethod
    def download_app(app_guid: str, app_version_guid: str, device_urlName: str, output_path: str = "app.PRG") -> None:
        """
        Downloads an application binary from the Garmin services and saves it to a specified file.

        Args:
            app_guid (str): The GUID of the app to download.
            app_version_guid (str): The version GUID of the app to download.
            device_urlName (str): The URL name of the device for which the app is intended.
            output_path (str): The path where the downloaded app binary will be saved. Defaults to *app.PRG*.

        Raises:
            Exception: If the download fails or if writing to the file fails.
        """

        resp = requests.get(f"https://services.garmin.com/appsLibraryBusinessServices_v0/rest/apps/{app_guid}/versions/{app_version_guid}/binaries/{device_urlName}")
        if resp.status_code != 200:
            raise Exception(f"Failed to download app, error {resp.status_code}:\n{resp.text}")
        try:
            with open(output_path, "wb") as f:
                f.write(resp.content)
        except Exception as e:
            raise Exception(f"Failed to write the app binaries to the file {output_path}: {e}")

    @staticmethod
    def download_app_settings(app_guid: str, app_version: int, firmware_part_number: str, locale: str = 'en-us', output_path: str = 'settings.SET') -> str:
        """
        Downloads the app settings for a given Garmin app and saves them to a specified file.

        Args:
            app_guid (str): The GUID of the Garmin app.
            app_version (int): The version of the Garmin app.
            firmware_part_number (str): The firmware part number of the device.
            locale (str): The locale for the settings page. Defaults to *en-us*.
            output_path (str): The path where the settings file will be saved. Defaults to *settings.SET*.

        Returns:
            path (str): The path to the saved settings file.

        Raises:
            Exception: If there is an error retrieving the HTML form or the settings file.
        """

        # Get the html form
        html_form = requests.get(f"https://apps.garmin.com/{locale}/appSettings2/{app_guid}/versions/{app_version}/devices/{firmware_part_number}/edit")
        if html_form.status_code != 200:
            raise Exception(f"Failed to get the html settigns form, error {html_form.status_code}:\n{html_form.text}")
        html_form = html_form.text
        # fix the links
        html_form = html_form.replace('="//', '="https://').replace('="/', '="https://apps.garmin.com/')
        # Add the validate button
        html_form = html_form.replace('</head>', "<script type='text/javascript'>document.addEventListener('DOMContentLoaded', function() {let btn = document.createElement('button');btn.innerHTML = 'Validate';btn.style.width = '100%';btn.style.backgroundColor = 'lightgreen';btn.style.minHeight = '70px';btn.style.fontSize = 'large';btn.style.fontWeight = 'bold';btn.addEventListener('click', function() {const settings_str = handleFormSubmit();if (settings_str != '' && settings_str !== undefined) {const xhr = new XMLHttpRequest();xhr.open('POST', '/');xhr.addEventListener('load', function() {close();});xhr.send(settings_str);}});document.body.appendChild(btn);});</script></head>")


        class Handler(BaseHTTPRequestHandler):
            done = False

            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html_form.encode())

            def do_POST(self):
                content_length = int(self.headers['Content-Length'])
                settings_string = self.rfile.read(content_length)

                # Get the binaries
                resp = requests.post(
                    f"https://apps.garmin.com/{locale}/appSettings2/{app_guid}/versions/{app_version}/devices/{firmware_part_number}/binary",
                    data=settings_string
                )
                if resp.status_code != 200:
                    raise Exception(f"Failed to retrieve the settings file, error {resp.status_code}:\n{resp.text}")

                # Write the settings file
                try:
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                except Exception as e:
                    raise Exception(f"Failed to write the settings file to the file {output_path}: {e}")

                # Send the response to close the window
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")

                # Close the server
                Handler.done = True

            def log_message(self, format, *args):
                return


        # open the local server
        server = HTTPServer(('localhost', 8080), Handler)
        webbrowser.open(f"http://localhost:8080")
        while not Handler.done:
            server.handle_request()
        server.server_close()
