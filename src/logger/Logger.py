from datetime import datetime
from pynput import keyboard
import sqlite3
import click

from logger.helpers import get_skipgram

DB_NAME = "logger.db"


class Logger:
    def __init__(self, session: str) -> None:
        self.listener: keyboard.Listener = keyboard.Listener(on_press=self.__on_press)
        self.log_unigrams: list[dict] = []
        self.log_bigrams: list[dict] = []
        self.log_trigrams: list[dict] = []
        self.last_saved: datetime
        self.session_name: str = session

    def __on_press(self, key) -> None:
        try:
            # Guard clause for special keys

            match key:
                case keyboard.Key.space:
                    key = "<space>"
                case keyboard.Key.down:
                    key = "<down>"
                case keyboard.Key.left:
                    key = "<left>"
                case keyboard.Key.right:
                    key = "<right>"
                case keyboard.Key.up:
                    key = "<up>"
                case keyboard.Key.esc:
                    key = "<esc>"
                case keyboard.Key.tab:
                    key = "<tab>"
                case _:
                    key = key.char

            current_key = {"name": key, "time": datetime.now()}

            try:
                # If current keypress is within 1 second of the last then log 2gram
                last_key = self.log_unigrams[-1]
                last_key_elapsed = current_key["time"] - last_key["time"]
                if last_key_elapsed.total_seconds() <= 1:
                    self.log_bigrams.append(
                        {
                            "name": last_key["name"] + current_key["name"],
                            "time": current_key["time"],
                        }
                    )

                # If current keypress is within 2 seconds of keypress before last
                # then log 3gram
                before_last_key = self.log_unigrams[-2]
                bf_last_key_elapsed = current_key["time"] - before_last_key["time"]
                if bf_last_key_elapsed.total_seconds() <= 2:
                    self.log_trigrams.append(
                        {
                            "name": before_last_key["name"]
                            + last_key["name"]
                            + current_key["name"],
                            "time": current_key["time"],
                        }
                    )

            # If current key is the first or second keypress ever, just ignore
            except IndexError:
                pass

            # Finally, log current key to 1gram always
            self.log_unigrams.append(current_key)

            # Save every 60 seconds and clear logs
            current_interval = current_key["time"] - self.last_saved
            if current_interval.total_seconds() >= 60:
                self.last_saved = datetime.now()
                self.__save_to_db(DB_NAME)
                self.log_unigrams.clear()
                self.log_bigrams.clear()
                self.log_trigrams.clear()

        except AttributeError:
            # When key.char doesn't exist
            pass
        except Exception as exception:
            click.echo(f"on_press exception: {exception}")

    def __db_init(self, db_name) -> None:
        try:
            con = sqlite3.connect(db_name)
            cur = con.cursor()

            cur.execute(
                "CREATE TABLE IF NOT EXISTS unigrams (id integer PRIMARY KEY, name, freq, session);"
            )
            cur.execute(
                "CREATE TABLE IF NOT EXISTS bigrams (id integer PRIMARY KEY, name, freq, session);"
            )
            cur.execute(
                "CREATE TABLE IF NOT EXISTS trigrams (id integer PRIMARY KEY, name, freq, session);"
            )
            cur.execute(
                "CREATE TABLE IF NOT EXISTS skipgrams (id integer PRIMARY KEY, name, weight, session);"
            )
            con.close()

        except Exception as exception:
            click.echo(f"__db_init exception: {exception}")

    def __save_to_db(self, db_name) -> None:
        try:
            con = sqlite3.connect(db_name)
            cur = con.cursor()
            logs = {
                "unigrams": self.log_unigrams,
                "bigrams": self.log_bigrams,
                "trigrams": self.log_trigrams,
            }
            for log_name in logs:
                for item in logs[log_name]:
                    name = item["name"]
                    res = cur.execute(
                        f"SELECT id FROM {log_name} WHERE name = ? AND session = ?",
                        (name, self.session_name),
                    ).fetchone()
                    if res is None:
                        cur.execute(
                            f"INSERT INTO {log_name} VALUES(NULL, ?, ?, ?)",
                            (name, 1, self.session_name),
                        )
                    else:
                        cur.execute(
                            f"UPDATE {log_name} SET freq = freq + 1 WHERE id = ?",
                            (res[0],),
                        )
            skipgrams = get_skipgram(self.log_unigrams)
            for key in skipgrams:
                res = cur.execute(
                    "SELECT id FROM skipgrams WHERE name = ? AND session = ?",
                    (key, self.session_name),
                ).fetchone()
                if res is None:
                    cur.execute(
                        "INSERT INTO skipgrams VALUES(NULL, ?, ?, ?)",
                        (key, skipgrams[key], self.session_name),
                    )
                else:
                    cur.execute(
                        "UPDATE skipgrams SET weight = weight + ? WHERE id = ?",
                        (skipgrams[key], res[0]),
                    )

            con.commit()
            con.close()

        except Exception as exception:
            click.echo(f"__save_to_db {exception = }")

    def start(self) -> None:
        if not self.listener.is_alive():
            self.last_saved = datetime.now()
            self.listener.start()
            self.listener.wait()
            self.__db_init(DB_NAME)
        else:
            click.echo("Logger is already running...")

    def stop(self) -> None:
        if self.listener.is_alive():
            self.end_time = datetime.now()
            self.listener.stop()
            self.__save_to_db(DB_NAME)
            click.echo("Session ended.")
        else:
            raise click.ClickException("Logging is not in session.")
