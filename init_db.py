"""Crea tablas, datos base y el usuario administrador en RDS."""
import os, pymysql
from werkzeug.security import generate_password_hash
c = pymysql.connect(host=os.environ["DB_HOST"], user=os.environ["DB_USER"],
                    password=os.environ.get("DB_PASS", ""), autocommit=True)
cur = c.cursor()
for stmt in open("schema.sql", encoding="utf8").read().split(";\n"):
    if stmt.strip(): cur.execute(stmt)
cur.execute("USE alerta_tacna")
cur.execute("INSERT IGNORE INTO usuarios (dni,nombre,telefono,email,password_hash,rol,distrito) VALUES (%s,%s,%s,%s,%s,'admin','Tacna')",
            ("00000001","Operador Central","052-000000","admin@alertatacna.pe",
             generate_password_hash(os.environ.get("ADMIN_PASS","Admin2026!"))))
print("Base de datos lista. Admin: admin@alertatacna.pe")