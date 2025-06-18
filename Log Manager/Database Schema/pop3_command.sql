-- POP3命令表
CREATE TABLE `pop3_command` (
  `command_id` int NOT NULL AUTO_INCREMENT,
  `pop3_session_id` int DEFAULT NULL,
  `command` text NOT NULL,
  `response` text NOT NULL,
  `timestamp` datetime NOT NULL,
  PRIMARY KEY (`command_id`),
  KEY `pop3_session_id` (`pop3_session_id`),
  CONSTRAINT `pop3_command_ibfk_1` FOREIGN KEY (`pop3_session_id`) REFERENCES `pop3_session` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4; 