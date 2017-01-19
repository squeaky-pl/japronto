import sys

from japronto.app import Application

reaper_settings = {
    'check_interval': int(sys.argv[1]),
    'idle_timeout': int(sys.argv[2])
}

app = Application(reaper_settings=reaper_settings)

if __name__ == '__main__':
    app.run()
