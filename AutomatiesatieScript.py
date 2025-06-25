import os
import shutil
import subprocess


EXAMPLE_TODO_PATH = "/var/www/html/vhosts/klant2.sil/"
EXAMPLE_WORDPRESS_PATH = "/var/www/html/vhosts/klant3.sil/wordpress/"
def create_zone(domein, zone_dir_domein):
    if not os.path.exists(zone_dir_domein):
        with open(zone_dir_domein, 'w') as zone_file:
            zone_file.write(f"""
$TTL 3H
@   IN  SOA  ns.{domein}. admin.{domein}. (
            2024093001 ; Serial
            1D          ; Refresh
            1H          ; Retry
            1W          ; Expire
            3H          ; Minimum
)

@   IN  NS   ns.{domein}.
ns  IN  A    192.168.1.1
www IN  A    192.168.1.1
            """)
        print(f"Zone file for {domein} created at {zone_dir_domein}")
    else:
        print(f"Zone file for {domein} already exists.")

def create_zone_in_named(domein):
    named_dir = "/etc/named.conf"
    if os.path.exists(named_dir):
        with open(named_dir, 'a') as named_file:
            named_file.write(f"""
zone "{domein}" IN {{
    type master;
    file "/var/named/{domein}";
}};
""")
        print(f"Zone voor {domein} toegevoegd aan named.conf")

def create_certificates(domein):
    cert_dir = f"/etc/httpd/ssl/{domein}/"
    os.makedirs(cert_dir, exist_ok=True)

    # Generate self-signed certificate
    cert_command = [
        "openssl", "req", "-x509", "-nodes", "-days", "365", "-newkey", "rsa:2048",
        "-keyout", f"{cert_dir}{domein}.key", "-out", f"{cert_dir}{domein}.crt",
        "-subj", f"/CN={domein}/O=MyOrg/C=NL"
    ]
    try:
        subprocess.run(cert_command, check=True)
        print(f"Certificaat voor {domein} aangemaakt en opgeslagen in {cert_dir}")
    except subprocess.CalledProcessError:
        print(f"Er ging iets mis bij het aanmaken van het certificaat voor {domein}.")

def setup_domein():
    domein_input = input("Welke naam wil je als website?").strip()
    if not domein_input.endswith(".sil"):
        domein = domein_input + ".sil"
    else:
        domein = domein_input

    print(f"Het volledige domein is: {domein}")

    zone_dir = "/var/named/"
    backup_dir = "/backup/"
    html_dir = "/var/www/html/vhosts/"
    db_name = domein.replace('.', '_')

    zone_dir_domein = zone_dir + domein
    html_dir_domein = html_dir + domein
    backup_dir_domein = backup_dir + domein

    # Controleer en maak een backup
    if os.path.exists(zone_dir_domein) or os.path.exists(html_dir_domein):
        # Maak een specifieke directory voor de backup van dit domein
        if not os.path.exists(backup_dir_domein):
            os.makedirs(backup_dir_domein)

        # Kopieer de bestanden naar de backupmap
        shutil.copy(zone_dir_domein, os.path.join(backup_dir_domein, f'zone{domein}'))

        if os.path.isdir(html_dir_domein):
            shutil.copytree(html_dir_domein, os.path.join(backup_dir_domein, 'html'))
        elif os.path.isfile(html_dir_domein):
            shutil.copy(html_dir_domein, os.path.join(backup_dir_domein, 'html'))

        print(f"Domein bestaat al. Backup opgeslagen in {backup_dir_domein}.")
        raise SystemExit("Domein bestaat al en is gebackupped.")


    # Maak de backup-directory aan als deze nog niet bestaat
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Check of map bestaat
    os.makedirs(html_dir_domein, exist_ok=True)

    # Maak de zone aan als deze nog niet bestaat
    create_zone(domein, zone_dir_domein)
    create_zone_in_named(domein)
    https_input = input("Wil je HTTPS gebruiken (ja/nee)? ").strip().lower()
    if https_input == "ja":
        create_https_vhost(domein)
        create_certificates(domein)
    elif https_input == "nee":
        create_http_vhost(domein)
    else:
        print("Ongeldige invoer, voer 'ja' of 'nee' in.")

    restart_services()
    create_db(domein)

def create_http_vhost(domein):
    domein_zonder_sil = domein.replace('.sil','')
    vhosts_dir_file = "/etc/httpd/conf.d/vhosts.conf"
    with open(vhosts_dir_file, 'a') as vhosts_file:
        vhosts_file.write(f"""
<VirtualHost *:8888>
    ServerName {domein}
    ServerAlias www.{domein}
    DocumentRoot "/var/www/html/vhosts/{domein}"
    ErrorDocument 403 "/var/www/html/custom_403.html"
    ErrorLog "/var/log/httpd/vhosts/{domein_zonder_sil}.error.log"
    CustomLog "/var/log/httpd/vhosts/{domein_zonder_sil}.access.log" combined
</VirtualHost>
    """)
    print(f"HTTP VirtualHost for {domein} created.")

def create_https_vhost(domein):
    domein_zonder_sil = domein.replace('.sil','')
    vhosts_dir_file = "/etc/httpd/conf.d/vhosts.conf"
    with open(vhosts_dir_file, 'a') as vhosts_file:
        vhosts_file.write(f"""
<VirtualHost *:8888>
    ServerName www.{domein}
    ServerAlias {domein}
    DocumentRoot "/var/www/html/vhosts/{domein}"
    ErrorDocument 403 "/var/www/html/custom_403.html"

    Redirect permanent / https://www.{domein}/
</VirtualHost>

<VirtualHost *:443>
    ServerName {domein}
    ServerAlias www.{domein}
    DocumentRoot "/var/www/html/vhosts/{domein}"
    ErrorDocument 403 "/var/www/html/custom_403.html"

    ErrorLog "/var/log/httpd/vhosts/{domein_zonder_sil}.error.log"
    CustomLog "/var/log/httpd/vhosts/{domein_zonder_sil}.access.log" combined
</VirtualHost>
    """)
    print(f"HTTPS VirtualHost for {domein} created.")

def create_static_html_site(domein):
    html_dir = f"/var/www/html/vhosts/{domein}"
    os.makedirs(html_dir, exist_ok=True)
    index_file = os.path.join(html_dir, "index.html")
    with open(index_file, 'w') as f:
        f.write(f"<html><head><title>{domein}</title></head><body><h1>Welkom bij {domein}</h1></body></html>")
    print(f"HTML site voor {domein} aangemaakt.")

def set_selinux_context(domein):
    wp_config_path = f"/var/www/html/vhosts/{domein}/wordpress/wp-config.php"

    # Het commando om SELinux context te wijzigen naar httpd_sys_rw_content_t (lees en schrijf)
    command = f"sudo chcon -t httpd_sys_rw_content_t {wp_config_path}"

    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    except subprocess.CalledProcessError as e:
        print(f"Fout bij het wijzigen van de SELinux: {e.stderr.decode()}")

def create_wordpress_files(domein, db_name, db_user, db_password):
    destination = f"/var/www/html/vhosts/{domein}/wordpress"
    os.makedirs(destination, exist_ok=True)
    shutil.copytree(EXAMPLE_WORDPRESS_PATH, destination, dirs_exist_ok=True)


    wp_config_path = os.path.join(destination, 'wp-config.php')
    set_selinux_context(domein)

    with open(wp_config_path, 'r') as file:
        config_data = file.read()
    config_data = config_data.replace('define( \'DB_NAME\', \'wordpress\' );', f'define( \'DB_NAME\', \'{db_name}\' );')
    config_data = config_data.replace('define( \'DB_USER\', \'klant3\' );', f'define( \'DB_USER\', \'{db_user}\' );')
    config_data = config_data.replace('define( \'DB_PASSWORD\', \'Azerty123!\' );', f'define( \'DB_PASSWORD\', \'{db_password}\' );')
    with open(wp_config_path, 'w') as file:
        file.write(config_data)
    print(f"WordPress files en wp-config.php aangepast voor {domein}.")


def update_todo_config(domein, db_name, db_user, db_password):
    config_path = f"/var/www/html/vhosts/{domein}/includes/config.php"

    # Zorg ervoor dat het configuratiebestand bestaat
    if os.path.exists(config_path):
        with open(config_path, 'r') as file:
            config_data = file.read()

        # Vervang de configuratiewaarden
        config_data = config_data.replace("define ('DB_HOST', 'localhost');", "define ('DB_HOST', 'localhost');")
        config_data = config_data.replace("define ('DB_USER', 'klant2');", f"define ('DB_USER', '{db_user}');")
        config_data = config_data.replace("define ('DB_PASS', 'Azerty123!');", f"define ('DB_PASS', '{db_password}');")
        config_data = config_data.replace("define ('DB_NAME', 'todo');", f"define ('DB_NAME', '{db_name}');")

        with open(config_path, 'w') as file:
            file.write(config_data)

        print(f"config.php aangepast voor {domein}.")
    else:
        print(f"Het config.php bestand bestaat niet in {config_path}.")



def move_sql_file(domein):
    source_sql_path = f"/var/www/html/vhosts/{domein}/todo.sql"
    destination_dir = "/opt/sql/"
    destination_sql_path = os.path.join(destination_dir, f"{domein}_todo.sql")

    # Zorg ervoor dat de bestemming bestaat
    os.makedirs(destination_dir, exist_ok=True)

    if os.path.exists(source_sql_path):
        # Verplaats het bestand naar /opt/sql
        shutil.move(source_sql_path, destination_sql_path)
        print(f"{source_sql_path} is verplaatst naar {destination_sql_path}")
    else:
        print(f"{source_sql_path} bestaat niet en kan niet worden verplaatst.")

def execute_sql_file(db_name, sql_file_path, db_password):
    command = f"mysql -u {db_name} -p'{db_password}' {db_name} < {sql_file_path}"
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"{sql_file_path} is geimporteerd in de database {db_name}")
    except subprocess.CalledProcessError:
        print(f"Er is een fout opgetreden bij het importeren van {sql_file_path}")

def create_todo_site(domein, db_name, db_user, db_password):
    destination = f"/var/www/html/vhosts/{domein}"
    os.makedirs(destination, exist_ok=True)

    # Kopieer alle bestanden en mappen uit de TODO-klant2 map naar doelmap
    for item in os.listdir(EXAMPLE_TODO_PATH):
        source = os.path.join(EXAMPLE_TODO_PATH, item)
        destination_item = os.path.join(destination, item)
        if os.path.isdir(source):
            shutil.copytree(source, destination_item, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination_item)

    move_sql_file(domein)

    # Update de SQL met de nieuwe databasenaam in de juiste locatie
    todo_sql_path = os.path.join('/opt/sql', f"{domein}_todo.sql")
    if os.path.exists(todo_sql_path):
        with open(todo_sql_path, 'r') as file:
            sql_data = file.read()

        sql_data = sql_data.replace('USE `todo`;', f'USE `{db_name}`;')

        with open(todo_sql_path, 'w') as file:
            file.write(sql_data)
    else:
        print(f"SQL-bestand {todo_sql_path} bestaat niet.")

    # Pas de configuratie aan in config.php met de juiste databasegegevens
    update_todo_config(domein, db_name, db_user, db_password)

    # Voer SQL-bestand uit
    try:
        execute_sql_file(db_name, todo_sql_path, db_password)
    except subprocess.CalledProcessError as e:
        print(f"Er ging iets mis bij het uitvoeren van de todo.sql file: {e}")

    print(f"TODO site bestanden en configuratie bijgewerkt voor {domein}.")


def create_wordpress(domein, db_name, db_user, db_password):
    wordpress_input = input("Wil je een WordPress website? (ja/nee) ").strip().lower()
    if wordpress_input == "ja":
        create_wordpress_files(domein, db_name, db_user, db_password)
    elif wordpress_input == "nee":
        create_todo_site(domein, db_name, db_user, db_password)
    else:
        print("Het antwoord moet ja of nee zijn!")

def restart_services():
    try:
        subprocess.run(["sudo", "systemctl", "restart", "httpd"], check=True)
        subprocess.run(["sudo", "systemctl", "restart", "named"], check=True)
        print("httpd en named services succesvol herstart.")
    except subprocess.CalledProcessError as e:
        print(f"Fout bij het herstarten van de services: {e}")

def create_db(domein):
    db_input = input("Wil je een databank aanmaken voor de site (ja/nee)? ").strip().lower()

    if db_input == "ja":
        db_name = input("Hoe moet deze noemen? ").strip()
        db_user = db_name
        db_password = input("Wat wil je als wachtwoord? ").strip()

        try:
            subprocess.run(["python3", "/opt/hostingscripts/createdb.py", db_name, db_user, db_password])
            create_wordpress(domein, db_name, db_user, db_password)
        except subprocess.CalledProcessError as e:
            print(f"Er ging iets mis bij het aanmaken van de databank: {e}")

    elif db_input == "nee":
        print(f"Er is geen database aangemaakt.")
        create_static_html_site(domein)
    else:
        print("Ongeldige invoer, voer 'ja' of 'nee' in.")

# Start het programma
setup_domein()
