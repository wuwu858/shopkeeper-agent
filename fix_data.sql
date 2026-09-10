USE dw;
TRUNCATE TABLE dim_region;
INSERT INTO dim_region (region_id, province, city, district) VALUES
(1, '广东省', '深圳市', '南山区'),
(2, '广东省', '广州市', '天河区'),
(3, '北京市', '北京市', '朝阳区'),
(4, '上海市', '上海市', '浦东新区');
SELECT * FROM dim_region;