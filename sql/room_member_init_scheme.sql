DROP TABLE IF EXISTS `room_member`;
CREATE TABLE `room_member` (
  `room_id` int NOT NULL,
  `user_id` int NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `score` int DEFAULT NULL,
  `select_difficulty` int NOT NULL,
  `token` varchar(255) DEFAULT NULL,
  `is_host` boolean DEFAULT 0,
  PRIMARY KEY (`room_id`, `user_id`)
);