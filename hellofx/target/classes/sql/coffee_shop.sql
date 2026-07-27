CREATE DATABASE IF NOT EXISTS `coffee_shop_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `coffee_shop_db`;

CREATE TABLE IF NOT EXISTS `product` (
  `p_id` int(11) NOT NULL AUTO_INCREMENT,
  `p_name` varchar(50) NOT NULL COMMENT '產品名稱',
  `p_price` int(11) NOT NULL COMMENT '單價',
  `p_category` varchar(30) NOT NULL COMMENT '分類：咖啡/茶飲/點心',
  `p_image` varchar(100) DEFAULT NULL COMMENT '圖片檔名',
  PRIMARY KEY (`p_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `product` (`p_name`, `p_price`, `p_category`, `p_image`) VALUES
('小農經典拿鐵', 120, '咖啡', 'latte.png'),
('衣索比亞手沖', 150, '咖啡', 'hand_drip.png'),
('燕麥奶焦糖瑪奇朵', 140, '咖啡', 'macchiato.png'),
('日月潭紅玉紅茶', 100, '茶飲', 'black_tea.png'),
('靜岡抹茶鮮奶', 130, '茶飲', 'matcha.png'),
('法式經典可麗露', 80, '點心', 'canele.png'),
('靜岡抹茶千層蛋糕', 140, '點心', 'matcha_cake.png'),
('熔岩巧克力布朗尼', 120, '點心', 'brownie.png');

CREATE TABLE IF NOT EXISTS `orders` (
  `o_id` int(11) NOT NULL AUTO_INCREMENT,
  `o_date` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '訂單時間',
  `table_num` varchar(10) NOT NULL COMMENT '桌號/外帶',
  `total_price` int(11) NOT NULL COMMENT '總金額',
  `status` varchar(20) DEFAULT '未製作' COMMENT '訂單狀態',
  PRIMARY KEY (`o_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `order_detail` (
  `od_id` int(11) NOT NULL AUTO_INCREMENT,
  `o_id` int(11) NOT NULL COMMENT '對應訂單編號',
  `p_id` int(11) NOT NULL COMMENT '對應產品編號',
  `quantity` int(11) NOT NULL COMMENT '數量',
  `subtotal` int(11) NOT NULL COMMENT '小計',
  `ice_level` varchar(20) DEFAULT '正常冰' COMMENT '冰量客製化',
  `sugar_level` varchar(20) DEFAULT '正常糖' COMMENT '甜度客製化',
  PRIMARY KEY (`od_id`),
  FOREIGN KEY (`o_id`) REFERENCES `orders` (`o_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;