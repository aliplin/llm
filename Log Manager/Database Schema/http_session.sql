-- HTTP会话表
CREATE TABLE `http_session` (
  `id` int NOT NULL AUTO_INCREMENT,
  `client_ip` varchar(45) NOT NULL,
  `start_time` datetime NOT NULL,
  `end_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4; 