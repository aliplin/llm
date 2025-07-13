-- MySQL会话表
CREATE TABLE `mysql_session` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `username` VARCHAR(255) NOT NULL,
  `time_date` DATETIME NOT NULL,
  `src_ip` VARCHAR(45) NOT NULL,
  `dst_ip` VARCHAR(45) NOT NULL,
  `src_port` INTEGER,
  `dst_port` INTEGER,
  `database_name` VARCHAR(255)
); 