"""Optional launcher for the earlier Tkinter desktop prototype."""

from pathlib import Path

from app import StudentInformationApp
from database import Database


if __name__ == "__main__":
    data_file = Path(__file__).with_name("student_information.db")
    StudentInformationApp(Database(data_file)).mainloop()
