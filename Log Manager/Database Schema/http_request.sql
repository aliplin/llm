-- HTTP请求表
CREATE TABLE `http_request` (
  `request_id` int NOT NULL AUTO_INCREMENT,
  `http_session_id` int DEFAULT NULL,
  `method` varchar(16) NOT NULL,
  `path` varchar(1024) NOT NULL,
  `headers` text,
  `request_time` datetime NOT NULL,
  `response` text NOT NULL,
  PRIMARY KEY (`request_id`),
  KEY `http_session_id` (`http_session_id`),
  CONSTRAINT `http_request_ibfk_1` FOREIGN KEY (`http_session_id`) REFERENCES `http_session` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4; 