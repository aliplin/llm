-- POP3会话表
CREATE TABLE `pop3_session` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(255) NOT NULL,
  `time_date` datetime NOT NULL,
  `src_ip` varchar(45) NOT NULL,
  `dst_ip` varchar(45) NOT NULL,
  `src_port` int DEFAULT NULL,
  `dst_port` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4; 