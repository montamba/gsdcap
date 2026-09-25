
-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: gsdparking
-- ------------------------------------------------------
-- Server version	8.0.45

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `admin`
--

DROP TABLE IF EXISTS `admin`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admin` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) DEFAULT NULL,
  `email` varchar(50) NOT NULL,
  `password` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admin`
--

LOCK TABLES `admin` WRITE;
/*!40000 ALTER TABLE `admin` DISABLE KEYS */;
INSERT INTO `admin` VALUES (1,'montamba','mon@mon','monmonmon');
/*!40000 ALTER TABLE `admin` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `history`
--

DROP TABLE IF EXISTS `history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `data` varchar(200) DEFAULT NULL,
  `guard` int DEFAULT NULL,
  `status` enum('failed','accepted','expired') DEFAULT NULL,
  `action` varchar(10) NOT NULL DEFAULT 'entry',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `plate` varchar(20) DEFAULT NULL,
  `department` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `guard` (`guard`),
  CONSTRAINT `history_ibfk_guard` FOREIGN KEY (`guard`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=67 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `history`
--

LOCK TABLES `history` WRITE;
/*!40000 ALTER TABLE `history` DISABLE KEYS */;
INSERT INTO `history` VALUES (64,NULL,3,'accepted','entry','2026-09-06 12:17:48','123ABC','VISITOR'),(65,NULL,3,'accepted','entry','2026-09-06 12:17:48',NULL,NULL),(66,NULL,3,'accepted','entry','2026-09-06 12:19:06','LLL222','COED');
/*!40000 ALTER TABLE `history` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `parking`
--

DROP TABLE IF EXISTS `parking`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `parking` (
  `id` int NOT NULL AUTO_INCREMENT,
  `available` int DEFAULT NULL,
  `occupied` int DEFAULT NULL,
  `total` int DEFAULT NULL,
  `total_occupied` float DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `parking`
--

LOCK TABLES `parking` WRITE;
/*!40000 ALTER TABLE `parking` DISABLE KEYS */;
INSERT INTO `parking` VALUES (1,18,2,20,1.5);
/*!40000 ALTER TABLE `parking` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `qrcode`
--

DROP TABLE IF EXISTS `qrcode`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `qrcode` (
  `id` int NOT NULL AUTO_INCREMENT,
  `data` varchar(200) DEFAULT NULL,
  `plate` varchar(50) NOT NULL,
  `owner_name` varchar(255) DEFAULT NULL,
  `owner_email` varchar(255) DEFAULT NULL,
  `owner_phone` varchar(20) DEFAULT NULL,
  `department` varchar(50) DEFAULT NULL,
  `expiry` datetime DEFAULT NULL,
  `status` varchar(20) DEFAULT 'active',
  `created_by` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `car_status` enum('IN','OUT') DEFAULT NULL,
  `vehicle_type` varchar(20) NOT NULL DEFAULT 'car',
  `space_units` tinyint NOT NULL DEFAULT '2',
  PRIMARY KEY (`id`),
  UNIQUE KEY `data` (`data`),
  KEY `fk_user` (`created_by`),
  CONSTRAINT `qrcode_ibfk_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `qrcode`
--

LOCK TABLES `qrcode` WRITE;
/*!40000 ALTER TABLE `qrcode` DISABLE KEYS */;
INSERT INTO `qrcode` VALUES (1,'GSD-CPAB-7SFX','123ABC','mon','monmon272005@gmail.com','09876543','visitor','2026-09-05 00:00:00','active',1,'2026-08-29 08:46:37',NULL,'car',2),(2,'GSD-VK3A-AMWY','123ABC','monmon','monmon272005@gmail.com','123','student','2026-09-05 00:00:00','active',1,'2026-08-29 09:27:24','IN','car',2),(3,'GSD-YEL7-ADZV','123ABC','teat','monmon272005@gmail.com','mon','visitor','2026-10-10 00:00:00','active',1,'2026-09-02 12:42:20','OUT','motorcycle',1),(4,'GSD-UFG5-AXTS','Test123','Mon','monmon272005@gmail.com',NULL,'visitor','2026-10-02 00:00:00','active',1,'2026-09-04 08:32:25',NULL,'car',2),(5,NULL,'123ABC','mon','michael@michael','098876',NULL,NULL,'active',7,'2026-09-05 05:12:19',NULL,'motorcycle',1),(6,NULL,'123ABC','mon','michael@michael','0909',NULL,NULL,'active',7,'2026-09-05 05:15:03',NULL,'car',2),(7,NULL,'123ABC','mon','michael@michael','0909',NULL,NULL,'active',7,'2026-09-05 05:16:25',NULL,'car',2),(8,NULL,'123ABC','mon','michael@michael','0909',NULL,NULL,'active',7,'2026-09-05 05:17:37',NULL,'car',2),(9,NULL,'123ABC','viy','michael@michael','',NULL,NULL,'active',7,'2026-09-05 05:17:55',NULL,'car',2),(10,NULL,'123ABC','viy','michael@michael','meme',NULL,NULL,'active',7,'2026-09-05 05:24:19',NULL,'car',2),(11,'GSD-W3PG0-ZXJLB','TRY123','Mob','michael@michael','0909',NULL,NULL,'active',7,'2026-09-05 06:30:14',NULL,'car',2),(12,NULL,'123ABC','kychu','michael@michael','',NULL,NULL,'active',7,'2026-09-10 08:42:52',NULL,'car',2),(13,'GSD-VNPXD-GQT3Z','123ABC','Fritz','michael@michael','',NULL,NULL,'active',7,'2026-09-17 02:13:52',NULL,'motorcycle',1);
/*!40000 ALTER TABLE `qrcode` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `qrpending`
--

DROP TABLE IF EXISTS `qrpending`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `qrpending` (
  `id` int NOT NULL AUTO_INCREMENT,
  `qrid` int DEFAULT NULL,
  `request_type` varchar(100) DEFAULT NULL,
  `request_by` int DEFAULT NULL,
  `actions` varchar(50) DEFAULT 'pending',
  `review_by` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `qrid` (`qrid`),
  KEY `request_by` (`request_by`),
  KEY `review_by` (`review_by`),
  CONSTRAINT `qrpending_ibfk_1` FOREIGN KEY (`qrid`) REFERENCES `qrcode` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `qrpending_ibfk_2` FOREIGN KEY (`request_by`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `qrpending_ibfk_3` FOREIGN KEY (`review_by`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `qrpending`
--

LOCK TABLES `qrpending` WRITE;
/*!40000 ALTER TABLE `qrpending` DISABLE KEYS */;
INSERT INTO `qrpending` VALUES (1,10,'request_qr',7,'pending',NULL),(2,11,'request_qr',7,'approved',1),(3,11,'qr_renewal',7,'pending',NULL),(4,12,'request_qr',7,'pending',NULL),(5,13,'request_qr',7,'approved',1);
/*!40000 ALTER TABLE `qrpending` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `request_history`
--

DROP TABLE IF EXISTS `request_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `request_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `request_description` varchar(50) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `created_by` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `created_by` (`created_by`),
  CONSTRAINT `request_history_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `request_history`
--

LOCK TABLES `request_history` WRITE;
/*!40000 ALTER TABLE `request_history` DISABLE KEYS */;
/*!40000 ALTER TABLE `request_history` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` enum('user','guard','staff') DEFAULT 'user',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `deletion_requested_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_deletion_requested` (`deletion_requested_at`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'fritz','fritz@fritz','$2b$12$901p7/3NpmLsdjDwtjNrPOumlAMoOPp/wvEibpBoNe5CMSnO1tFm2','staff','2026-08-29 08:45:59',NULL),(2,'mon','mon@mon','$2b$12$orVOARZqGpZ9JG9adeWA2enTen3k8Oeaz.3AMGDwHWY/LrSV3NRWG','guard','2026-08-29 09:25:41',NULL),(3,'viy','viy@viy','$2b$12$FgGd.IZede716Axy/t.l2.f/hSxOQIYI5V/kGi8B05qjO0gs/c1J2','guard','2026-09-02 12:08:36',NULL),(4,'godwin','godwin@godwin','$2b$12$Ri0vansvPsC.sCEA51/FTutmy6546OK7aAJse2cmUPjfYuvZpZAfW','guard','2026-09-02 12:09:11',NULL),(5,'carl','carl@carl','$2b$12$sbz5eYnGqbyYyOq4icLv9.02Rpqsl1Gu8lRnezY/Ximlioz84y1JG','guard','2026-09-02 12:10:07',NULL),(6,'ela','ela@ela','$2b$12$i7by3pWNQkmK0pijUBK/W.tv4PzpYMXioreEZczCbyBMoAapN8pVG','guard','2026-09-02 12:10:40',NULL),(7,'michael','michael@michael','$2b$12$OYLGrBLWO0pwOlBFy7gEvOdOzs5FuMNa4twukFTKIo9S1m0eWfcli','user','2026-09-05 05:11:35',NULL),(9,'monmon','monmon272005@gmail.com','$2b$12$TTpLH3xibhpsq/iP7hUmXeITVYzwwXbgDptThzYKCnRHH6lhDkrAu','user','2026-09-05 08:11:55',NULL);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-25  9:29:02
