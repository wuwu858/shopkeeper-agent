-- MySQL dump 10.13  Distrib 8.0.46, for Linux (x86_64)
--
-- Host: localhost    Database: meta
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `meta`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `meta` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `meta`;

--
-- Table structure for table `column_deny_list`
--

DROP TABLE IF EXISTS `column_deny_list`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `column_deny_list` (
  `id` int NOT NULL AUTO_INCREMENT,
  `column_name` varchar(100) COLLATE utf8mb4_general_ci NOT NULL COMMENT '字段名',
  `table_name` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '表名',
  `description` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '说明',
  `role_whitelist` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '允许查看的角色(逗号分隔)',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='敏感列配置表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `column_deny_list`
--

LOCK TABLES `column_deny_list` WRITE;
/*!40000 ALTER TABLE `column_deny_list` DISABLE KEYS */;
INSERT INTO `column_deny_list` VALUES (1,'cost_price','fact_order','成本价','admin,manager','2026-08-19 07:09:51'),(2,'profit_margin','fact_order','利润率','admin','2026-08-19 07:09:51'),(3,'customer_phone','dim_customer','客户电话','admin,manager','2026-08-19 07:09:51'),(4,'cost_price','fact_order','成本价','admin,manager','2026-08-19 07:11:59'),(5,'profit_margin','fact_order','利润率','admin','2026-08-19 07:11:59'),(6,'customer_phone','dim_customer','客户电话','admin,manager','2026-08-19 07:11:59');
/*!40000 ALTER TABLE `column_deny_list` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `column_info`
--

DROP TABLE IF EXISTS `column_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `column_info` (
  `id` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `type` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `role` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `examples` json DEFAULT NULL,
  `description` text COLLATE utf8mb4_general_ci,
  `alias` json DEFAULT NULL,
  `table_id` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `column_info`
--

LOCK TABLES `column_info` WRITE;
/*!40000 ALTER TABLE `column_info` DISABLE KEYS */;
INSERT INTO `column_info` VALUES ('dim_region.province','province','varchar','dimension','[\"广东省\", \"北京市\", \"上海市\", \"广西壮族自治区\", \"海南省\"]','省份名称','[\"省份\", \"省\"]','dim_region'),('dim_region.region_id','region_id','int','dimension','[\"1\", \"2\", \"3\", \"4\", \"5\", \"6\", \"7\"]','地区ID','[\"地区编号\"]','dim_region'),('fact_order.order_amount','order_amount','decimal','measure','[\"100.50\", \"200.00\", \"150.75\", \"300.00\", \"250.00\"]','订单金额','[\"金额\", \"销售额\", \"订单金额\"]','fact_order'),('fact_order.order_id','order_id','varchar','dimension','[\"ORD001\", \"ORD002\", \"ORD003\", \"ORD004\", \"ORD005\"]','订单ID','[\"订单编号\"]','fact_order'),('fact_order.product_name','product_name','varchar','dimension',NULL,'产品名称','[\"产品\", \"商品\"]','fact_order'),('fact_order.region','region','varchar','dimension','[\"华南\", \"华东\", \"西南\", \"华北\", \"华中\"]','订单所属地区','[\"地区\", \"区域\"]','fact_order'),('fact_order.region_id','region_id','int','dimension','[\"1\", \"3\", \"4\"]','地区ID','[\"所属地区\"]','fact_order'),('fact_order.sales_amt','sales_amt','decimal','measure',NULL,'订单销售金额','[\"金额\", \"成交额\", \"销售额\"]','fact_order');
/*!40000 ALTER TABLE `column_info` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `column_metric`
--

DROP TABLE IF EXISTS `column_metric`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `column_metric` (
  `column_id` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `metric_id` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`column_id`,`metric_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `column_metric`
--

LOCK TABLES `column_metric` WRITE;
/*!40000 ALTER TABLE `column_metric` DISABLE KEYS */;
INSERT INTO `column_metric` VALUES ('fact_order.order_amount','GMV'),('fact_order.order_amount','销售总额'),('fact_order.sales_amt','销售总额');
/*!40000 ALTER TABLE `column_metric` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dimension_dict`
--

DROP TABLE IF EXISTS `dimension_dict`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dimension_dict` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_general_ci NOT NULL COMMENT '维度名称',
  `category` varchar(50) COLLATE utf8mb4_general_ci NOT NULL COMMENT '维度分类: region, time, product, customer',
  `mapping_values` text COLLATE utf8mb4_general_ci COMMENT '映射值(JSON)',
  `description` text COLLATE utf8mb4_general_ci COMMENT '说明',
  `alias` text COLLATE utf8mb4_general_ci COMMENT '同义词(JSON)',
  `is_active` tinyint DEFAULT '1' COMMENT '是否启用',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name_category` (`name`,`category`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='维度字典表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dimension_dict`
--

LOCK TABLES `dimension_dict` WRITE;
/*!40000 ALTER TABLE `dimension_dict` DISABLE KEYS */;
INSERT INTO `dimension_dict` VALUES (1,'华北','region','[\"北京市\",\"天津市\",\"河北省\",\"山西省\",\"内蒙古自治区\"]','华北地区省份','[\"华北地区\",\"华北区域\"]',1,'2026-08-21 08:28:25','2026-08-21 08:28:25'),(2,'华南','region','[\"广东省\",\"广西壮族自治区\",\"海南省\"]','华南地区省份','[\"华南地区\",\"华南区域\"]',1,'2026-08-21 08:28:25','2026-08-21 08:28:25'),(3,'华东','region','[\"上海市\",\"江苏省\",\"浙江省\",\"安徽省\",\"福建省\",\"江西省\",\"山东省\"]','华东地区省份','[\"华东地区\",\"华东区域\"]',1,'2026-08-21 08:28:25','2026-08-21 08:28:25');
/*!40000 ALTER TABLE `dimension_dict` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `metric_dict`
--

DROP TABLE IF EXISTS `metric_dict`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `metric_dict` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_general_ci NOT NULL COMMENT '指标名称',
  `description` text COLLATE utf8mb4_general_ci COMMENT '指标定义/口径',
  `expression` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '计算公式',
  `relevant_columns` text COLLATE utf8mb4_general_ci COMMENT '依赖字段(JSON)',
  `alias` text COLLATE utf8mb4_general_ci COMMENT '同义词(JSON)',
  `is_active` tinyint DEFAULT '1' COMMENT '是否启用',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='指标字典表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `metric_dict`
--

LOCK TABLES `metric_dict` WRITE;
/*!40000 ALTER TABLE `metric_dict` DISABLE KEYS */;
INSERT INTO `metric_dict` VALUES (1,'GMV','成交总额，所有已支付订单的金额总和','SUM(order_amount)','[\"fact_order.order_amount\"]','[\"销售总额\", \"成交额\", \"订单总额\", \"总销售额\"]',1,'2026-08-21 08:28:25','2026-08-21 08:28:25'),(2,'AOV','客单价，每笔订单的平均金额','AVG(order_amount)','[\"fact_order.order_amount\"]','[\"平均客单价\", \"单均价\"]',1,'2026-08-21 08:28:25','2026-08-21 08:28:25');
/*!40000 ALTER TABLE `metric_dict` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `metric_info`
--

DROP TABLE IF EXISTS `metric_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `metric_info` (
  `id` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `description` text COLLATE utf8mb4_general_ci,
  `relevant_columns` json DEFAULT NULL,
  `alias` json DEFAULT NULL,
  `expression` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `metric_info`
--

LOCK TABLES `metric_info` WRITE;
/*!40000 ALTER TABLE `metric_info` DISABLE KEYS */;
INSERT INTO `metric_info` VALUES ('GMV','GMV','全称 Gross Merchandise Value，表示所有订单的成交金额总和。','[\"fact_order.order_amount\"]','[\"成交总额\", \"订单总额\"]',NULL),('metric_GMV','GMV','全称 Gross Merchandise Value，表示所有订单的成交金额总和。','[\"fact_order.order_amount\"]',NULL,NULL),('metric_销售总额','销售总额','所有订单的金额总和','[\"fact_order.order_amount\"]',NULL,NULL);
/*!40000 ALTER TABLE `metric_info` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `query_audit`
--

DROP TABLE IF EXISTS `query_audit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `query_audit` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` varchar(50) COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户ID',
  `user_name` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户名',
  `query_text` text COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户原始问题',
  `generated_sql` text COLLATE utf8mb4_general_ci COMMENT '生成的SQL',
  `exec_status` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '执行状态: pending/success/error/denied',
  `exec_time` int DEFAULT NULL COMMENT '执行耗时(毫秒)',
  `return_rows` int DEFAULT NULL COMMENT '返回行数',
  `llm_token` int DEFAULT NULL COMMENT 'LLM Token消耗',
  `err_msg` text COLLATE utf8mb4_general_ci COMMENT '错误信息',
  `ip_address` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户端IP',
  `user_agent` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'User-Agent',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_status` (`exec_status`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='查询审计日志表，禁止删除';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `query_audit`
--

LOCK TABLES `query_audit` WRITE;
/*!40000 ALTER TABLE `query_audit` DISABLE KEYS */;
/*!40000 ALTER TABLE `query_audit` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sys_user`
--

DROP TABLE IF EXISTS `sys_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_user` (
  `id` varchar(50) COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户ID',
  `username` varchar(100) COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户名',
  `password` varchar(255) COLLATE utf8mb4_general_ci NOT NULL COMMENT '密码(bcrypt加密)',
  `role` varchar(50) COLLATE utf8mb4_general_ci DEFAULT 'viewer' COMMENT '角色: admin/sales/manager/viewer',
  `department` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '部门',
  `real_name` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '真实姓名',
  `email` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '邮箱',
  `is_active` tinyint DEFAULT '1' COMMENT '是否启用',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统用户表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sys_user`
--

LOCK TABLES `sys_user` WRITE;
/*!40000 ALTER TABLE `sys_user` DISABLE KEYS */;
INSERT INTO `sys_user` VALUES ('user_001','zhangsan','$2b$12$W.p2z/eNlZq89MVR4GTSaeGxA4wV5pig12QIoYRQez2sudzHAa4E.','sales','销售部','张三',NULL,1,'2026-08-19 07:09:51','2026-08-19 07:36:06'),('user_002','lisi','$2b$12$W.p2z/eNlZq89MVR4GTSaeGxA4wV5pig12QIoYRQez2sudzHAa4E.','manager','销售部','李四',NULL,1,'2026-08-19 07:09:51','2026-08-19 07:36:06'),('user_003','admin','$2b$12$W.p2z/eNlZq89MVR4GTSaeGxA4wV5pig12QIoYRQez2sudzHAa4E.','admin','','管理员',NULL,1,'2026-08-19 07:09:51','2026-08-19 07:36:06'),('user_004','wangwu','$2b$12$W.p2z/eNlZq89MVR4GTSaeGxA4wV5pig12QIoYRQez2sudzHAa4E.','viewer','市场部','王五',NULL,1,'2026-08-19 07:09:51','2026-08-19 07:36:06');
/*!40000 ALTER TABLE `sys_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `table_info`
--

DROP TABLE IF EXISTS `table_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `table_info` (
  `id` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `role` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `description` text COLLATE utf8mb4_general_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `table_info`
--

LOCK TABLES `table_info` WRITE;
/*!40000 ALTER TABLE `table_info` DISABLE KEYS */;
INSERT INTO `table_info` VALUES ('dim_region','dim_region','dim','地区维度表'),('fact_order','fact_order','fact','订单事实表');
/*!40000 ALTER TABLE `table_info` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_region_perm`
--

DROP TABLE IF EXISTS `user_region_perm`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_region_perm` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` varchar(50) COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户ID',
  `region` varchar(50) COLLATE utf8mb4_general_ci NOT NULL COMMENT '允许访问的地区: 华北/华南/华东/华中/西南/西北/东北',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_region` (`user_id`,`region`),
  CONSTRAINT `user_region_perm_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户地区权限表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_region_perm`
--

LOCK TABLES `user_region_perm` WRITE;
/*!40000 ALTER TABLE `user_region_perm` DISABLE KEYS */;
INSERT INTO `user_region_perm` VALUES (1,'user_001','华北','2026-08-19 07:09:51'),(2,'user_001','华南','2026-08-19 07:09:51'),(3,'user_002','华北','2026-08-19 07:09:51'),(4,'user_002','华南','2026-08-19 07:09:51'),(5,'user_002','华东','2026-08-19 07:09:51'),(6,'user_004','华南','2026-08-19 07:09:51');
/*!40000 ALTER TABLE `user_region_perm` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'meta'
--

--
-- Current Database: `dw`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `dw` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `dw`;

--
-- Table structure for table `dim_region`
--

DROP TABLE IF EXISTS `dim_region`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_region` (
  `region_id` int NOT NULL,
  `province` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `city` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `district` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`region_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_region`
--

LOCK TABLES `dim_region` WRITE;
/*!40000 ALTER TABLE `dim_region` DISABLE KEYS */;
INSERT INTO `dim_region` VALUES (1,'广东省','深圳市','南山区'),(2,'广东省','广州市','天河区'),(3,'北京市','北京市','朝阳区'),(4,'上海市','上海市','浦东新区'),(5,'广东省',NULL,NULL),(6,'广西壮族自治区',NULL,NULL),(7,'海南省',NULL,NULL);
/*!40000 ALTER TABLE `dim_region` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `fact_order`
--

DROP TABLE IF EXISTS `fact_order`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fact_order` (
  `order_id` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `order_date` date DEFAULT NULL,
  `product_id` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `product_name` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `category` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `region` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `quantity` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `order_amount` decimal(10,2) DEFAULT NULL,
  `region_id` int DEFAULT NULL,
  `new_region_id` int DEFAULT NULL,
  PRIMARY KEY (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `fact_order`
--

LOCK TABLES `fact_order` WRITE;
/*!40000 ALTER TABLE `fact_order` DISABLE KEYS */;
INSERT INTO `fact_order` VALUES ('ORD001','2026-07-01','P001',NULL,NULL,NULL,NULL,'2026-07-26 14:45:54',100.50,1,NULL),('ORD002','2026-07-02','P002',NULL,NULL,NULL,NULL,'2026-07-26 14:45:54',200.00,1,NULL),('ORD003','2026-07-03','P001',NULL,NULL,NULL,NULL,'2026-07-26 14:45:54',150.75,3,NULL),('ORD004','2026-07-04','P003',NULL,NULL,NULL,NULL,'2026-07-26 14:45:54',300.00,4,NULL),('ORD005','2026-07-05','P002',NULL,NULL,NULL,NULL,'2026-07-26 14:45:54',250.00,3,NULL);
/*!40000 ALTER TABLE `fact_order` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Temporary view structure for view `fact_order_sales`
--

DROP TABLE IF EXISTS `fact_order_sales`;