-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)
--
-- Host: mysql-36706bc7-monmon272005-2233.d.aivencloud.com    Database: gsdparking
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
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ '1feb7f61-3b05-11f1-90d5-82a14058c561:1-107,
45e9ba21-3175-11f1-b280-5e11fe6e03fe:1-60,
726a3f61-33ab-11f1-9a8b-d60a44377ce0:1-15,
b2c061fd-34bd-11f1-a0fc-26bccfa5fcca:1-27';

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
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
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
  `action` varchar(10) NOT NULL DEFAULT 'entry' COMMENT 'entry or exit',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'when the scan happened',
  `ownername` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `guard` (`guard`),
  CONSTRAINT `history_ibfk_guard` FOREIGN KEY (`guard`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=56 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `history`
--

LOCK TABLES `history` WRITE;
/*!40000 ALTER TABLE `history` DISABLE KEYS */;
INSERT INTO `history` VALUES (4,'GSD-D2AC-GT6B',17,'accepted','entry','2026-04-23 11:36:25',NULL),(5,'GSD-D2AC-GT6B',17,'accepted','entry','2026-04-23 11:36:25',NULL),(6,'GSD-D2AC-GT6B',17,'accepted','entry','2026-04-23 11:36:25',NULL),(7,'GSD-D2AC-GT6B',17,'failed','entry','2026-04-23 11:36:25',NULL),(8,'GSD-D2AC-GT6B',17,'accepted','entry','2026-04-23 11:36:25',NULL),(9,'GSD-D2AC-GT6B',17,'accepted','entry','2026-04-23 11:36:25',NULL),(10,'GSD-D2AC-GT6B',17,'failed','entry','2026-04-23 11:36:25',NULL),(11,'GSD-D2AC-GT6B',17,'failed','entry','2026-04-23 11:36:25',NULL),(12,'GSD-D2AC-GT6B',17,'accepted','entry','2026-04-23 11:36:25',NULL),(13,'GSD-D2AC-GT6B',17,'accepted','entry','2026-04-23 11:36:25',NULL),(14,'GSD-D2AC-GT6B',17,'accepted','entry','2026-04-23 11:36:25',NULL),(15,'GSD-D2AC-GT6B',17,'accepted','entry','2026-04-23 11:36:25',NULL),(16,'GSD-D2AC-GT6B',17,'failed','entry','2026-04-23 11:36:25',NULL),(17,'GSD-Y8MQ-27PM',17,'expired','entry','2026-04-23 11:36:25',NULL),(18,'GSD-KQW6-Z5ZW',17,'failed','entry','2026-05-25 04:51:56',NULL),(19,'GSD-KQW6-Z5ZW',17,'failed','entry','2026-05-25 04:52:07',NULL),(20,'GSD-FUXM-GM9X',17,'accepted','entry','2026-05-25 04:53:15',NULL),(21,'GSD-7PHV-CACV',17,'accepted','entry','2026-05-25 04:59:28',NULL),(22,'GSD-7PHV-CACV',17,'failed','entry','2026-05-25 05:04:50',NULL),(23,'GSD-7PHV-CACV',17,'failed','exit','2026-05-25 05:05:23',NULL),(24,'GSD-7PHV-CACV',17,'accepted','exit','2026-05-25 05:07:50',NULL),(25,'GSD-7PHV-CACV',17,'failed','entry','2026-05-25 05:08:07',NULL),(26,'GSD-FUXM-GM9X',17,'accepted','exit','2026-05-25 05:08:26',NULL),(27,'GSD-KQW6-Z5ZW',17,'failed','entry','2026-05-25 05:08:51',NULL),(28,'GSD-7PHV-CACV',17,'accepted','entry','2026-05-25 05:09:05',NULL),(29,'GSD-28SU-JVZP',17,'accepted','entry','2026-06-01 07:13:45',NULL),(30,'GSD-28SU-JVZP',17,'failed','entry','2026-06-01 07:14:02',NULL),(31,'GSD-28SU-JVZP',17,'accepted','exit','2026-06-01 07:14:17',NULL),(32,'GSD-28SU-JVZP',17,'accepted','entry','2026-06-01 08:53:57',NULL),(33,'GSD-28SU-JVZP',17,'failed','entry','2026-06-01 08:54:25',NULL),(34,'GSD-28SU-JVZP',17,'accepted','exit','2026-06-01 08:54:39',NULL),(35,'GSD-L48Y-78WV',17,'failed','entry','2026-06-01 18:43:19',NULL),(36,'GSD-DGG6-FNHB',17,'failed','entry','2026-06-02 09:44:08',NULL),(37,'GSD-DGG6-FNHB',17,'failed','entry','2026-06-02 09:44:11',NULL),(38,'GSD-DGG6-FNHB',17,'failed','entry','2026-06-02 09:44:13',NULL),(39,'GSD-DGG6-FNHB',17,'failed','entry','2026-06-02 09:44:14',NULL),(40,'GSD-DGG6-FNHB',17,'failed','entry','2026-06-02 09:44:18',NULL),(41,'GSD-DGG6-FNHB',17,'failed','entry','2026-06-02 09:44:22',NULL),(42,'GSD-DGG6-FNHB',17,'failed','entry','2026-06-02 09:44:24',NULL),(43,'GSD-DGG6-FNHB',17,'failed','entry','2026-06-02 09:45:00',NULL),(44,'GSD-DGG6-FNHB',17,'failed','entry','2026-06-02 09:45:04',NULL),(45,'GSD-WCGG-PHHX',17,'failed','entry','2026-06-02 12:24:38',NULL),(46,'GSD-WCGG-PHHX',17,'failed','exit','2026-06-02 12:24:53',NULL),(47,'GSD-WCGG-PHHX',17,'failed','entry','2026-06-02 12:25:03',NULL),(48,'GSD-WCGG-PHHX',17,'failed','entry','2026-06-02 12:25:42',NULL),(49,'GSD-WCGG-PHHX',17,'failed','entry','2026-06-02 12:25:47',NULL),(50,'GSD-5YCX-B8CT',17,'accepted','entry','2026-06-03 17:27:14',NULL),(51,'GSD-5YCX-B8CT',17,'accepted','exit','2026-06-03 17:27:42',NULL),(52,'GSD-5YCX-B8CT',17,'accepted','entry','2026-06-03 17:28:29',NULL),(53,'GSD-TURA-VGVS',17,'accepted','entry','2026-06-03 17:31:59',NULL),(54,'GSD-54TP-J3WD',17,'accepted','entry','2026-06-03 17:32:12',NULL),(55,'GSD-54TP-J3WD',17,'accepted','exit','2026-06-03 17:34:49',NULL);
/*!40000 ALTER TABLE `history` ENABLE KEYS */;
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
  `expiry` datetime DEFAULT NULL,
  `status` varchar(20) DEFAULT 'active',
  `created_by` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `car_status` enum('IN','OUT') DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `data` (`data`),
  KEY `fk_user` (`created_by`),
  CONSTRAINT `qrcode_ibfk_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `qrcode`
--

LOCK TABLES `qrcode` WRITE;
/*!40000 ALTER TABLE `qrcode` DISABLE KEYS */;
INSERT INTO `qrcode` VALUES (19,'GSD-26Z8-XY5K','ABC-123','mavi D','mavilyndiaz@gmail.com','2027-10-13 00:00:00','active',23,'2026-06-03 17:13:56',NULL),(20,'GSD-CU3U-2EAU','ABC-123','mavi D','mavilyndiaz@gmail.com','2028-07-13 00:00:00','active',23,'2026-06-03 17:14:59',NULL),(21,'GSD-5YCX-B8CT','ACB_123','mabi B','mavilyndiaz@gmail.com','2029-06-05 00:00:00','active',23,'2026-06-03 17:26:12','IN'),(22,'GSD-54TP-J3WD','ABS-234','viy.viy','mavilyndiaz@gmail.com','2026-06-04 00:00:00','active',23,'2026-06-03 17:29:39','OUT'),(23,'GSD-TURA-VGVS','ABD-907','viy marie','mavilyndiaz@gmail.com','2026-06-16 00:00:00','active',23,'2026-06-03 17:30:32','IN'),(24,'GSD-C58U-K2XP','ssssddd','','monmon272005@gmail.com','2026-06-13 00:00:00','active',18,'2026-06-04 13:15:26',NULL);
/*!40000 ALTER TABLE `qrcode` ENABLE KEYS */;
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
  `deletion_requested_at` datetime DEFAULT NULL COMMENT 'Set when user requests account deletion; NULL = active',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_deletion_requested` (`deletion_requested_at`)
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (17,'fritz','fritz@fritz','$2b$12$TTxYnvIiWYQk/twob6hHguTmp8ZEfQrHVdjWAysKOolzsuYMvOXC.','guard','2026-04-06 06:55:50',NULL),(18,'godwin','godwin@godwin','$2b$12$bBpfCipfnIx.n.tafNfCyuNriPoyi/kpwVipnDV20cft54FU.eGFO','staff','2026-04-21 12:54:24',NULL),(19,'nick','nbsiaotong.ui@phinmaed.com','$2b$12$G2pP7X7cLRUDW93PpMeCVua9uMZIsFn.9ekD46yzzYQf4yB5aT.pa','staff','2026-06-01 08:47:16',NULL),(21,'marie','viymariee@gmail.com','$2b$12$jQIFI8v/wJc6U7k5H8JReupJRnxYI1Y7UBuudi98t.42LnT11dWgu','guard','2026-06-02 10:05:13',NULL),(22,'viya','viy@gmail.com','$2b$12$ditxFjux.hXX2hkMGIRj1udjv70aCULdMraSsaSqhz3lFOfGbqBTe','staff','2026-06-02 10:07:50',NULL),(23,'marieviy','via@gmail.com','$2b$12$BCM7G6GE./X/L2rBPgdCdeQa4LRCGbjuYU5cLzX6TYaidQrV7i/.S','staff','2026-06-02 12:12:12',NULL);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-05  8:34:14
