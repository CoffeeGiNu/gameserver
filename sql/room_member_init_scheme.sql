DROP TABLE IF EXISTS `room_member`;
CREATE TABLE `room_member` (
  `room_id` int NOT NULL,
  `user_id` int NOT NULL,
  `judge_perfect` int DEFAULT NULL,
  `judge_great` int DEFAULT NULL,
  `judge_good` int DEFAULT NULL,
  `judge_bad` int DEFAULT NULL,
  `judge_miss` int DEFAULT NULL,
  `score` bigint DEFAULT NULL,
  `select_difficulty` int NOT NULL,
  `token` varchar(255) DEFAULT NULL,
  `is_host` boolean DEFAULT 0
);