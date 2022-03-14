DROP TABLE IF EXISTS `room`;
CREATE TABLE `room` (
  `room_id` int NOT NULL AUTO_INCREMENT,
  `live_id` int DEFAULT 0,
  `joined_user_count` int DEFAULT 0,
  `max_user_count` int DEFAULT 4,
  PRIMARY KEY (`room_id`)
);