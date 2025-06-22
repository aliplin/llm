-- MySQL命令表
CREATE TABLE `mysql_command` (
  `command_id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `mysql_session_id` INTEGER,
  `command` TEXT NOT NULL,
  `response` TEXT NOT NULL,
  `timestamp` DATETIME NOT NULL,
  `command_type` VARCHAR(50),
  `affected_rows` INTEGER,
  FOREIGN KEY (`mysql_session_id`) REFERENCES `mysql_session` (`id`)
); 