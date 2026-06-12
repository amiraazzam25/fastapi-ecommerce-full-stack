import pyodbc

drivers = [d for d in pyodbc.drivers()]
print("Available ODBC Drivers:")
for d in drivers:
    print(f" - {d}")