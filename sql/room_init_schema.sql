DROP TABLE IF EXISTS `room`;
CREATE TABLE `room` (
  `room_id` int NOT NULL AUTO_INCREMENT,
  `live_id` int NOT NULL,
  `host` int NOT NULL,
  `max_user_count` int DEFAULT 4,
  `joined_user_count` int DEFAULT 1,
  `status` int DEFAULT 1,
  PRIMARY KEY (`room_id`)
);