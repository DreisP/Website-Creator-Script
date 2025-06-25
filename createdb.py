#!/usr/bin/python3
import sys 
import pymysql as mysql 


database_name = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]

response = input("Creating database " + database_name + " and user " + username + " with password " + password +" Is this ok? (y/n) ")

if response.lower() in ['y', 'yes']:
    try:
        connection = mysql.connect(
        host='localhost',
        user='root',
        password='')

        cursor = connection.cursor()
        create_db_query = f"CREATE DATABASE IF NOT EXISTS `{database_name}`;"
        cursor.execute(create_db_query)
        print(f"`{database_name}` db aangemaakt")

        create_user_query = f"CREATE USER IF NOT EXISTS '{username}'@'localhost' IDENTIFIED BY '{password}';"
        cursor.execute(create_user_query)
        print(f"`{username}` user met wachtwoord '{password}' gecreëerd")

        give_privileges = f"GRANT ALL PRIVILEGES ON `{database_name}`.* TO '{username}'@'localhost';"
        privileges_reload = f"FLUSH PRIVILEGES;"

        cursor.execute(give_privileges)
        print(f"`{username}` privileges op '{database_name}' database gegeven ")

        cursor.execute(privileges_reload)
        print("Privileges herlaad")

        cursor.execute(f"SHOW GRANTS FOR '{username}'@'localhost';")
        grants = cursor.fetchall()
        cursor.execute(f"USE `{database_name}`;")
        create_users_table_query = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_users_table_query)
        print("Tabel 'users' aangemaakt")

        insert_user_query = f"INSERT INTO users (username, password) VALUES ('{username}', '{password}') ON DUPLICATE KEY UPDATE password='{password}';"
        cursor.execute(insert_user_query)
        print(f"Gebruiker '{username}' toegevoegd aan de tabel 'users'")

        connection.commit()
    except mysql.MySQLError as err:
        print("Fout gebeurt tijdens db maken:")
        print(err)
        if connection:
            connection.rollback()

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
else:
    print("Exiting")
