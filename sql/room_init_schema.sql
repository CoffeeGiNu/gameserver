DROP TABLE IF EXISTS `room`;
CREATE TABLE `room` (
  `room_id` int NOT NULL AUTO_INCREMENT,
  `token` varchar(255) DEFAULT NULL,
  `live_id` int DEFAULT 0,
  `joined_user_count` int DEFAULT 0,
  `max_user_count` int DEFAULT 4,
  PRIMARY KEY (`room_id`),
  UNIQUE KEY `token` (`token`)
);