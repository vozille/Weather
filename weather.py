import requests
import json
import signal
import gi
from gi.repository import Gtk, AppIndicator3, GObject
import subprocess
gi.require_version('Gtk', '3.0')


# add error handling

"""
Constants
"""

DEFAULT_DATA_PATH = "/home/anwesh/code/myapps/projects/Weather/defaults.json"
DEFAULT_RAW_DATA = "/home/anwesh/code/myapps/projects/Weather/data.txt"
DEFAULT_ICON_PATH = "/home/anwesh/code/myapps/projects/Weather/icon.png"


def get_city():
    """
    check first if user has manually set a city
    :return:
    """
    with open(DEFAULT_DATA_PATH) as file:
        data = json.load(file)
    if data["city"] != "auto":
        return data["city"]
    send_url = 'http://freegeoip.net/json'
    try:
        request = requests.get(send_url)
        if request.status_code == 200:
            json_data = json.loads(request.text)
            lat = json_data["latitude"]
            long = json_data["longitude"]
            return json_data["city"]
        else:
            return None
    except requests.ConnectionError:
        return None


def get_weather():
    city = get_city()
    # no internet
    if city is None:
        print('no internet connection')
        with open(DEFAULT_RAW_DATA) as file:
            data = json.load(file)
        return data

    try:
        params = {'APPID': '1d02acb0a01b4471272e58de491565e4', 'q': city.lower(), 'units': 'metric'}
        print(params)
        city_weather = requests.get('http://api.openweathermap.org/data/2.5/weather?', params=params)
        # internet connection lost midway
        if city_weather.status_code == 200:
            weather_details = json.loads(city_weather.text)
            print(weather_details)
            icon_link_url = 'http://openweathermap.org/img/w/' + weather_details["weather"][0]["icon"] + '.png'
            icon = requests.get(icon_link_url, stream=True)
            if icon.status_code == 200:
                with open(DEFAULT_ICON_PATH, 'wb') as f:
                    for chunk in icon:
                        f.write(chunk)
            data = dict()
            data["city"] = city
            data["temp"] = str(
                round(float((weather_details["main"]["temp_max"]) + float(weather_details["main"]["temp_min"])) / 2, 2)
            )
            data["weather"] = weather_details["weather"][0]["description"]

            data["humidity"] = str(weather_details["main"]["humidity"])
            data["wind"] = str(weather_details["wind"]["speed"])

            """
            date returned is in epoch/unix time.. convert to human readable time
            the data from shell is in bytes
            convert to string and strip newline character
            """
            sunrise = subprocess.check_output(
                    "date --date='@" + str(weather_details["sys"]["sunrise"]) +
                    "' '+%r'", shell=True)
            data["sunrise"] = sunrise.decode("utf-8").strip('\n')
            sunset = subprocess.check_output(
                "date --date='@" + str(weather_details["sys"]["sunset"]) +
                "' '+%r'", shell=True)
            data["sunset"] = sunset.decode("utf-8").strip('\n')

            with open(DEFAULT_RAW_DATA, 'w') as file:
                json.dump(data, file)

            return data
        else:
            print('no internet connection')
            with open(DEFAULT_RAW_DATA) as file:
                data = json.load(file)
                return data
    except requests.ConnectionError:
        print('we lost internet connection')
        with open(DEFAULT_RAW_DATA) as file:
            data = json.load(file)
            return data


class Indicator:
    def __init__(self, data):
        self.app = 'weather_app'
        self.indicator = AppIndicator3.Indicator.new(
            self.app, DEFAULT_ICON_PATH,
            AppIndicator3.IndicatorCategory.OTHER)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.create_menu(data))
        self.indicator.set_label(data["city"] + " : " + data["temp"] + " °C", self.app)
        # sets the reload timer, in milliseconds
        GObject.timeout_add(1000*60*10, self.refresh)

    def refresh(self):
        data = get_weather()
        self.indicator.set_menu(self.create_menu(data))
        self.indicator.set_label(data["city"] + " : " + data["temp"] + " °C", self.app)
        return True

    def create_menu(self, data):
        menu = Gtk.Menu()
        # menu item 1
        item_1 = Gtk.MenuItem('today: '+data["weather"])
        menu.append(item_1)
        item_2 = Gtk.MenuItem('humidity: '+data["humidity"]+'%')
        menu.append(item_2)
        item_3 = Gtk.MenuItem('wind-speed: ' + data["wind"] + 'km/hr')
        menu.append(item_3)
        item_4 = Gtk.MenuItem('sunrise: ' + data["sunrise"])
        menu.append(item_4)
        item_5 = Gtk.MenuItem('sunset: ' + data["sunset"])
        menu.append(item_5)
        menu_sep = Gtk.SeparatorMenuItem()
        menu.append(menu_sep)
        item3 = Gtk.MenuItem("Change City")
        item3.connect('activate', self.entry)
        menu.append(item3)
        menu_sep = Gtk.SeparatorMenuItem()
        menu.append(menu_sep)
        item_quit = Gtk.MenuItem('Quit')
        item_quit.connect('activate', self.quit)
        menu.append(item_quit)

        menu.show_all()
        return menu

    def entry(self, src):
        SettingsWindow()

    def quit(self, src):
        exit(0)


class SettingsWindow:
    def __init__(self):
        # create a new window
        self.window = Gtk.Window()
        self.window.set_size_request(200, 100)
        self.window.set_title("Settings")
        self.window.connect("delete_event", self.quit)

        self.vbox = Gtk.VBox(False, 0)
        self.window.add(self.vbox)
        self.vbox.show()

        self.entry = Gtk.Entry()
        self.entry.set_max_length(20)
        self.entry.set_text("Enter City name")
        self.vbox.pack_start(self.entry, False, True, 0)
        self.entry.show()

        self.hbox = Gtk.HBox(False, 0)
        self.vbox.add(self.hbox)
        self.hbox.show()

        self.check = Gtk.CheckButton("AutoDetect City")
        self.hbox.pack_start(self.check, True, True, 0)
        self.check.set_active(False)
        self.check.show()

        self.button = Gtk.Button("Done")
        self.button.connect("clicked", self.enter_callback)
        self.vbox.pack_start(self.button, True, True, 0)
        self.button.grab_default()
        self.button.show()
        self.window.show()

    def enter_callback(self, src):

        entry_text = self.entry.get_text()
        if not self.check.get_active():
            with open(DEFAULT_DATA_PATH, 'r') as file:
                data = json.load(file)
            data["city"] = entry_text.lower()
            print(data)
            with open(DEFAULT_DATA_PATH, 'w') as file:
                json.dump(data, file)
        else:
            with open(DEFAULT_DATA_PATH, 'r') as file:
                data = json.load(file)
            data["city"] = "auto"
            with open(DEFAULT_DATA_PATH, 'w') as file:
                json.dump(data, file)
        self.window.destroy()
        tray.refresh()

    def quit(self, src, foo):
        del self.window

tray = None


def main():
    global tray
    stats = get_weather()
    tray = Indicator(stats)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()

if __name__ == '__main__':
    main()
