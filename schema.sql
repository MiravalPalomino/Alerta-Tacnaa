CREATE DATABASE IF NOT EXISTS alerta_tacna CHARACTER SET utf8mb4;
USE alerta_tacna;

CREATE TABLE comisarias (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  distrito VARCHAR(60) NOT NULL,
  direccion VARCHAR(150),
  telefono VARCHAR(20),
  lat DECIMAL(9,6), lng DECIMAL(9,6)
);
CREATE TABLE usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  dni CHAR(8) NOT NULL UNIQUE,
  nombre VARCHAR(100) NOT NULL,
  telefono VARCHAR(20),
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  rol ENUM('ciudadano','operador','admin') NOT NULL DEFAULT 'ciudadano',
  distrito VARCHAR(60),
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE contactos_emergencia (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  nombre VARCHAR(100) NOT NULL,
  telefono VARCHAR(20) NOT NULL,
  parentesco VARCHAR(40),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);
CREATE TABLE efectivos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  comisaria_id INT NOT NULL,
  nombre VARCHAR(100) NOT NULL,
  grado VARCHAR(40),
  unidad VARCHAR(60) COMMENT 'patrullero / serenazgo / motorizado',
  disponible TINYINT(1) DEFAULT 1,
  FOREIGN KEY (comisaria_id) REFERENCES comisarias(id)
);
CREATE TABLE alertas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  tipo ENUM('robo','agresion','accidente','sospechoso','emergencia_medica','otro') NOT NULL DEFAULT 'otro',
  descripcion VARCHAR(255),
  lat DECIMAL(9,6) NOT NULL, lng DECIMAL(9,6) NOT NULL,
  estado ENUM('pendiente','asignada','en_camino','atendida','falsa') NOT NULL DEFAULT 'pendiente',
  comisaria_id INT,
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  FOREIGN KEY (comisaria_id) REFERENCES comisarias(id),
  INDEX (estado), INDEX (creado_en)
);
CREATE TABLE ubicaciones_alerta (
  id INT AUTO_INCREMENT PRIMARY KEY,
  alerta_id INT NOT NULL,
  lat DECIMAL(9,6) NOT NULL, lng DECIMAL(9,6) NOT NULL,
  registrado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (alerta_id) REFERENCES alertas(id) ON DELETE CASCADE
);
CREATE TABLE atenciones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  alerta_id INT NOT NULL,
  efectivo_id INT NOT NULL,
  operador_id INT NOT NULL,
  asignado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  cerrado_en TIMESTAMP NULL,
  observaciones VARCHAR(255),
  FOREIGN KEY (alerta_id) REFERENCES alertas(id),
  FOREIGN KEY (efectivo_id) REFERENCES efectivos(id),
  FOREIGN KEY (operador_id) REFERENCES usuarios(id)
);
CREATE TABLE notificaciones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  alerta_id INT NOT NULL,
  contacto_id INT NOT NULL,
  canal ENUM('sms','whatsapp','email') DEFAULT 'sms',
  mensaje VARCHAR(300),
  enviado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (alerta_id) REFERENCES alertas(id) ON DELETE CASCADE,
  FOREIGN KEY (contacto_id) REFERENCES contactos_emergencia(id)
);
CREATE TABLE historial_estados (
  id INT AUTO_INCREMENT PRIMARY KEY,
  alerta_id INT NOT NULL,
  estado_anterior VARCHAR(20),
  estado_nuevo VARCHAR(20) NOT NULL,
  usuario_id INT,
  cambiado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (alerta_id) REFERENCES alertas(id) ON DELETE CASCADE
);

INSERT INTO comisarias (nombre,distrito,direccion,telefono,lat,lng) VALUES
('Comisaría de Tacna','Tacna','Av. Bolognesi, Tacna','052-411111',-18.0146,-70.2536),
('Comisaría Alto de la Alianza','Alto de la Alianza','Av. Collpa, Alto de la Alianza','052-412222',-17.9950,-70.2400),
('Comisaría Ciudad Nueva','Ciudad Nueva','Ciudad Nueva, Tacna','052-413333',-17.9780,-70.2380),
('Comisaría Gregorio Albarracín','Gregorio Albarracín','Av. Industrial, G. Albarracín','052-414444',-18.0500,-70.2500),
('Comisaría Pocollay','Pocollay','Pocollay, Tacna','052-415555',-17.9980,-70.2200);
INSERT INTO efectivos (comisaria_id,nombre,grado,unidad) VALUES
(1,'Carlos Mamani','Suboficial','Patrullero 01'),(1,'Luis Condori','Suboficial','Motorizado 02'),
(2,'Jorge Quispe','Sargento','Patrullero 03'),(3,'Ana Flores','Alférez','Patrullero 04'),
(4,'Pedro Ticona','Suboficial','Serenazgo 05'),(5,'Rosa Apaza','Sargento','Patrullero 06');
