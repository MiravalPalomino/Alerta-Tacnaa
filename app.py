import os, math, pymysql
from functools import wraps
from flask import Flask, request, jsonify, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev")

def db():
    return pymysql.connect(host=os.environ["DB_HOST"], user=os.environ["DB_USER"],
        password=os.environ.get("DB_PASS", ""), database=os.environ.get("DB_NAME", "alerta_tacna"),
        cursorclass=pymysql.cursors.DictCursor, autocommit=True)

def q(sql, args=(), one=False, write=False):
    con = db()
    try:
        with con.cursor() as cur:
            cur.execute(sql, args)
            if write: return cur.lastrowid
            return cur.fetchone() if one else cur.fetchall()
    finally:
        con.close()

def login_required(roles=None):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            if "uid" not in session: return jsonify(error="No autenticado"), 401
            if roles and session["rol"] not in roles: return jsonify(error="Sin permiso"), 403
            return f(*a, **k)
        return w
    return deco

def dist(a, b, c, d):  # km (haversine)
    p = math.pi / 180
    h = 0.5 - math.cos((c-a)*p)/2 + math.cos(a*p)*math.cos(c*p)*(1-math.cos((d-b)*p))/2
    return 12742 * math.asin(math.sqrt(h))

@app.route("/")
def index(): return render_template("index.html")

@app.route("/health")
def health():
    q("SELECT 1"); return jsonify(ok=True)

@app.post("/api/registro")
def registro():
    d = request.json
    try:
        uid = q("INSERT INTO usuarios (dni,nombre,telefono,email,password_hash,distrito) VALUES (%s,%s,%s,%s,%s,%s)",
                (d["dni"], d["nombre"], d.get("telefono"), d["email"], generate_password_hash(d["password"]), d.get("distrito")), write=True)
    except pymysql.err.IntegrityError:
        return jsonify(error="DNI o correo ya registrado"), 409
    return jsonify(id=uid), 201

@app.post("/api/login")
def login():
    d = request.json
    u = q("SELECT * FROM usuarios WHERE email=%s", (d["email"],), one=True)
    if not u or not check_password_hash(u["password_hash"], d["password"]):
        return jsonify(error="Credenciales inválidas"), 401
    session.update(uid=u["id"], rol=u["rol"], nombre=u["nombre"])
    return jsonify(nombre=u["nombre"], rol=u["rol"])

@app.post("/api/logout")
def logout(): session.clear(); return jsonify(ok=True)

@app.get("/api/yo")
def yo():
    if "uid" not in session: return jsonify(rol=None)
    return jsonify(nombre=session["nombre"], rol=session["rol"])

@app.route("/api/contactos", methods=["GET", "POST"])
@login_required()
def contactos():
    if request.method == "POST":
        d = request.json
        i = q("INSERT INTO contactos_emergencia (usuario_id,nombre,telefono,parentesco) VALUES (%s,%s,%s,%s)",
              (session["uid"], d["nombre"], d["telefono"], d.get("parentesco")), write=True)
        return jsonify(id=i), 201
    return jsonify(q("SELECT * FROM contactos_emergencia WHERE usuario_id=%s", (session["uid"],)))

@app.post("/api/alertas")
@login_required()
def crear_alerta():
    d = request.json
    lat, lng = float(d["lat"]), float(d["lng"])
    coms = q("SELECT id,lat,lng FROM comisarias")
    cerca = min(coms, key=lambda c: dist(lat, lng, float(c["lat"]), float(c["lng"])))
    aid = q("INSERT INTO alertas (usuario_id,tipo,descripcion,lat,lng,comisaria_id) VALUES (%s,%s,%s,%s,%s,%s)",
            (session["uid"], d.get("tipo", "otro"), d.get("descripcion"), lat, lng, cerca["id"]), write=True)
    q("INSERT INTO ubicaciones_alerta (alerta_id,lat,lng) VALUES (%s,%s,%s)", (aid, lat, lng), write=True)
    q("INSERT INTO historial_estados (alerta_id,estado_anterior,estado_nuevo,usuario_id) VALUES (%s,NULL,'pendiente',%s)", (aid, session["uid"]), write=True)
    for c in q("SELECT id FROM contactos_emergencia WHERE usuario_id=%s", (session["uid"],)):
        q("INSERT INTO notificaciones (alerta_id,contacto_id,mensaje) VALUES (%s,%s,%s)",
          (aid, c["id"], f"ALERTA de {session['nombre']}: ubicación https://maps.google.com/?q={lat},{lng}"), write=True)
    return jsonify(id=aid, comisaria_id=cerca["id"]), 201

@app.post("/api/alertas/<int:aid>/ubicacion")
@login_required()
def seguimiento(aid):
    d = request.json
    q("INSERT INTO ubicaciones_alerta (alerta_id,lat,lng) VALUES (%s,%s,%s)", (aid, d["lat"], d["lng"]), write=True)
    return jsonify(ok=True)

@app.get("/api/mis-alertas")
@login_required()
def mis_alertas():
    return jsonify(q("""SELECT a.id,a.tipo,a.estado,a.creado_en,c.nombre comisaria FROM alertas a
        LEFT JOIN comisarias c ON c.id=a.comisaria_id WHERE a.usuario_id=%s ORDER BY a.id DESC LIMIT 20""", (session["uid"],)), )

@app.get("/api/panel/alertas")
@login_required(["operador", "admin"])
def panel():
    return jsonify(q("""SELECT a.id,a.tipo,a.descripcion,a.lat,a.lng,a.estado,a.creado_en,
        u.nombre ciudadano,u.telefono,c.nombre comisaria FROM alertas a
        JOIN usuarios u ON u.id=a.usuario_id LEFT JOIN comisarias c ON c.id=a.comisaria_id
        ORDER BY FIELD(a.estado,'pendiente','asignada','en_camino','atendida','falsa'), a.id DESC LIMIT 100"""))

@app.get("/api/efectivos")
@login_required(["operador", "admin"])
def efectivos():
    return jsonify(q("SELECT e.id,e.nombre,e.unidad,c.nombre comisaria FROM efectivos e JOIN comisarias c ON c.id=e.comisaria_id WHERE e.disponible=1"))

@app.post("/api/panel/alertas/<int:aid>/asignar")
@login_required(["operador", "admin"])
def asignar(aid):
    eid = request.json["efectivo_id"]
    q("INSERT INTO atenciones (alerta_id,efectivo_id,operador_id) VALUES (%s,%s,%s)", (aid, eid, session["uid"]), write=True)
    q("UPDATE efectivos SET disponible=0 WHERE id=%s", (eid,), write=True)
    cambiar(aid, "asignada")
    return jsonify(ok=True)

def cambiar(aid, nuevo):
    a = q("SELECT estado FROM alertas WHERE id=%s", (aid,), one=True)
    q("UPDATE alertas SET estado=%s WHERE id=%s", (nuevo, aid), write=True)
    q("INSERT INTO historial_estados (alerta_id,estado_anterior,estado_nuevo,usuario_id) VALUES (%s,%s,%s,%s)",
      (aid, a["estado"], nuevo, session["uid"]), write=True)
    if nuevo in ("atendida", "falsa"):
        q("UPDATE efectivos SET disponible=1 WHERE id IN (SELECT efectivo_id FROM atenciones WHERE alerta_id=%s)", (aid,), write=True)
        q("UPDATE atenciones SET cerrado_en=NOW() WHERE alerta_id=%s", (aid,), write=True)

@app.post("/api/panel/alertas/<int:aid>/estado")
@login_required(["operador", "admin"])
def estado(aid):
    nuevo = request.json["estado"]
    if nuevo not in ("en_camino", "atendida", "falsa"): return jsonify(error="Estado inválido"), 400
    cambiar(aid, nuevo); return jsonify(ok=True)

@app.get("/api/reportes")
@login_required(["operador", "admin"])
def reportes():
    return jsonify(
        por_estado=q("SELECT estado, COUNT(*) total FROM alertas GROUP BY estado"),
        por_tipo=q("SELECT tipo, COUNT(*) total FROM alertas GROUP BY tipo"),
        por_comisaria=q("SELECT c.nombre, COUNT(*) total FROM alertas a JOIN comisarias c ON c.id=a.comisaria_id GROUP BY c.nombre"),
        tiempo_prom_min=q("""SELECT ROUND(AVG(TIMESTAMPDIFF(MINUTE,a.creado_en,t.asignado_en)),1) minutos
                             FROM alertas a JOIN atenciones t ON t.alerta_id=a.id""", one=True))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
