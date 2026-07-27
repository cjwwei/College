package com.example;

import javafx.application.Application;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.Scene;
import javafx.scene.control.*;
import javafx.scene.layout.*;
import javafx.stage.Stage;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;

public class App extends Application {

    private final String[][] products = {
        {"小農經典拿鐵", "120", "咖啡"},
        {"衣索比亞手沖", "150", "咖啡"},
        {"燕麥奶焦糖瑪奇朵", "140", "咖啡"},
        {"日月潭紅玉紅茶", "100", "茶飲"},
        {"靜岡抹茶鮮奶", "130", "茶飲"},
        {"法式經典可麗露", "80", "點心"},
        {"靜岡抹茶千層蛋糕", "140", "點心"},
        {"熔岩巧克力布朗尼", "120", "點心"}
    };

    private GridPane productGrid;
    private TableView<String[]> cartTable;
    private Label totalLabel;
    private int totalPrice = 0;

    @Override
    public void start(Stage primaryStage) {
        // 採用 BorderPane (最適合平板點餐的三欄式佈局)
        BorderPane root = new BorderPane();
        root.setPadding(new Insets(15));

        // 分類導覽列 觸控按鈕等
        VBox leftMenu = new VBox(15);
        leftMenu.setPadding(new Insets(10));
        leftMenu.setPrefWidth(160);
        
        Button btnAll = new Button("全部商品");
        Button btnCoffee = new Button("精品咖啡");
        Button btnTea = new Button("在地茶飲");
        Button btnDessert = new Button("精緻點心");
        
        // 套用 CSS 樣式類別 (定義在 style.css 中)
        btnAll.getStyleClass().add("btn-primary");
        btnCoffee.getStyleClass().add("btn-primary");
        btnTea.getStyleClass().add("btn-primary");
        btnDessert.getStyleClass().add("btn-primary");
        
        // 讓按鈕寬度填滿左側欄
        btnAll.setMaxWidth(Double.MAX_VALUE);
        btnCoffee.setMaxWidth(Double.MAX_VALUE);
        btnTea.setMaxWidth(Double.MAX_VALUE);
        btnDessert.setMaxWidth(Double.MAX_VALUE);

        // 綁定點擊事件：切換不同商品分類
        btnAll.setOnAction(e -> showProducts("全部"));
        btnCoffee.setOnAction(e -> showProducts("咖啡"));
        btnTea.setOnAction(e -> showProducts("茶飲"));
        btnDessert.setOnAction(e -> showProducts("點心"));
        
        leftMenu.getChildren().addAll(btnAll, btnCoffee, btnTea, btnDessert);
        root.setLeft(leftMenu);

        // 3. 中間 (Center): 產品卡片展示區 (GridPane)
        productGrid = new GridPane();
        productGrid.setHgap(20);
        productGrid.setVgap(20);
        productGrid.setPadding(new Insets(10));
        
        // 程式啟動 預設載入全部商品
        showProducts("全部");
        
        // 加上滾動軸 避免產品過多時超出平板畫面
        ScrollPane scrollPane = new ScrollPane(productGrid);
        scrollPane.setFitToWidth(true);
        root.setCenter(scrollPane);

        // 購物車明細與功能區
        VBox rightCart = new VBox(15);
        rightCart.setPadding(new Insets(10));
        rightCart.setPrefWidth(280);

        Label cartTitle = new Label("購物車明細 (桌號: 05)");
        cartTitle.setStyle("-fx-font-size: 18px; -fx-font-weight: bold;");

        // 購物車表格設定
        cartTable = new TableView<>();
        TableColumn<String[], String> colName = new TableColumn<>("品項");
        colName.setCellValueFactory(data -> new javafx.beans.property.SimpleStringProperty(data.getValue()[0]));
        TableColumn<String[], String> colPrice = new TableColumn<>("價格");
        colPrice.setCellValueFactory(data -> new javafx.beans.property.SimpleStringProperty(data.getValue()[1]));
        
        cartTable.getColumns().add(colName);
        cartTable.getColumns().add(colPrice);
        cartTable.setPrefHeight(350); // 固定高度，留空間給下方的刪除與結帳按鈕

        // 刪除選定品項按鈕
        Button btnDelete = new Button("刪除選定品項");
        btnDelete.setStyle("-fx-background-color: #f0ad4e; -fx-text-fill: white; -fx-font-size: 14px; -fx-font-weight: bold;");
        btnDelete.setMaxWidth(Double.MAX_VALUE);
        btnDelete.setPrefHeight(40);
        btnDelete.setOnAction(e -> deleteSelectedSelection());

        // 總金額
        totalLabel = new Label("總計金額: $0");
        totalLabel.setStyle("-fx-font-size: 20px; -fx-font-weight: bold; -fx-text-fill: #d9534f;");

        // 送出訂單按鈕
        Button btnCheckout = new Button("確認送出訂單");
        btnCheckout.getStyleClass().add("btn-success");
        btnCheckout.setMaxWidth(Double.MAX_VALUE);
        btnCheckout.setPrefHeight(50);
        btnCheckout.setOnAction(e -> handleCheckout());

        rightCart.getChildren().addAll(cartTitle, cartTable, btnDelete, totalLabel, btnCheckout);
        root.setRight(rightCart);

        // 建立視窗並載入 Bootstrap CSS
        Scene scene = new Scene(root, 960, 600);
        try {
            // 讀取 src/main/resources/css/style.css
            String css = getClass().getResource("/css/style.css").toExternalForm();
            scene.getStylesheets().add(css);
        } catch (Exception e) {
            System.out.println("提示：找不到 style.css 樣式檔，將採用預設外觀呈現。");
        }

        primaryStage.setTitle("JW-Coffee_Shop - 平板自助點餐系統");
        primaryStage.setScene(scene);
        primaryStage.show();
    }

    // 📌 功能一：動態分類篩選商品卡片
    private void showProducts(String category) {
        productGrid.getChildren().clear();
        int column = 0;
        int row = 0;

        for (String[] prod : products) {
            String prodName = prod[0];
            String prodPrice = prod[1];
            String prodCategory = prod[2];

            if (category.equals("全部") || prodCategory.equals(category)) {
                VBox card = new VBox(10);
                card.getStyleClass().add("product-card");
                card.setAlignment(Pos.CENTER);
                card.setPrefSize(180, 200);

                Label nameLabel = new Label(prodName);
                nameLabel.setStyle("-fx-font-size: 16px; -fx-font-weight: bold;");
                
                Label priceLabel = new Label("$" + prodPrice);
                priceLabel.setStyle("-fx-font-size: 14px; -fx-text-fill: #888;");
                
                Button btnAdd = new Button("加入購物車");
                btnAdd.getStyleClass().add("btn-primary");
                btnAdd.setOnAction(e -> addToCart(prodName, Integer.parseInt(prodPrice)));

                card.getChildren().addAll(nameLabel, priceLabel, btnAdd);

                productGrid.add(card, column, row);
                column++;
                if (column == 2) { // 每排放 2 個商品 符合平板排版
                    column = 0;
                    row++;
                }
            }
        }
    }

    // 點擊餐點加入購物車
    private void addToCart(String name, int price) {
        cartTable.getItems().add(new String[]{name, String.valueOf(price)});
        totalPrice += price;
        totalLabel.setText("總計金額: $" + totalPrice);
    }

    // 刪除購物車中被選取的品項
    private void deleteSelectedSelection() {
        String[] selectedItem = cartTable.getSelectionModel().getSelectedItem();

        if (selectedItem != null) {
            int itemPrice = Integer.parseInt(selectedItem[1]);
            totalPrice -= itemPrice;
            cartTable.getItems().remove(selectedItem);
            totalLabel.setText("總計金額: $" + totalPrice);
            cartTable.getSelectionModel().clearSelection();
        } else {
            Alert alert = new Alert(Alert.AlertType.WARNING, "請先在購物車清單中，點選您想要刪除的餐點喔！", ButtonType.OK);
            alert.setTitle("溫馨提示");
            alert.setHeaderText(null);
            alert.showAndWait();
        }
    }

    // 確認送出訂單並即時寫入 MySQL 資料庫 (JDBC)
    private void handleCheckout() {
        if (cartTable.getItems().isEmpty()) {
            // 當購物車為空會跳出警告
            Alert alert = new Alert(Alert.AlertType.WARNING, "購物車是空的喔！", ButtonType.OK);
            alert.showAndWait();
            return;
        }

        // 資料庫連線路徑
        String url = "jdbc:mysql://localhost:3306/coffee_shop_db?useSSL=false&serverTimezone=UTC&allowPublicKeyRetrieval=true";
        String user = "root";
        String password = "";

        Connection conn = null;
        PreparedStatement psOrder = null;
        PreparedStatement psDetail = null;

        try {
            conn = DriverManager.getConnection(url, user, password);
            conn.setAutoCommit(false); // 關閉自動提交，開啟 Transaction 安全防護機制

            // orders
            String insertOrderSql = "INSERT INTO orders (table_num, total_price, status) VALUES (?, ?, ?)";
            psOrder = conn.prepareStatement(insertOrderSql, Statement.RETURN_GENERATED_KEYS);
            psOrder.setString(1, "05"); // 綁定平板固定的桌號 05
            psOrder.setInt(2, totalPrice);
            psOrder.setString(3, "未製作");
            psOrder.executeUpdate();

            // o_id
            int orderId = 0;
            ResultSet generatedKeys = psOrder.getGeneratedKeys();
            if (generatedKeys.next()) {
                orderId = generatedKeys.getInt(1);
            }

            //  將商品選項送到 order_detail
            String insertDetailSql = "INSERT INTO order_detail (o_id, p_id, quantity, subtotal) VALUES (?, ?, ?, ?)";
            psDetail = conn.prepareStatement(insertDetailSql);

            for (String[] item : cartTable.getItems()) {
                String prodName = item[0];
                int price = Integer.parseInt(item[1]);

                // 根據商品名稱，對應資料庫中預導的 p_id 產品編號
                int productId = 1; 
                if (prodName.contains("手沖")) productId = 2;
                else if (prodName.contains("瑪奇朵")) productId = 3;
                else if (prodName.contains("紅茶")) productId = 4;
                else if (prodName.contains("鮮奶")) productId = 5;
                else if (prodName.contains("可麗露")) productId = 6;
                else if (prodName.contains("千層")) productId = 7;
                else if (prodName.contains("布朗尼")) productId = 8;

                psDetail.setInt(1, orderId);
                psDetail.setInt(2, productId);
                psDetail.setInt(3, 1); 
                psDetail.setInt(4, price);
                
                psDetail.addBatch();
            }
            psDetail.executeBatch();

            conn.commit();

            // 彈出成功通知
            Alert alert = new Alert(Alert.AlertType.INFORMATION, "點餐成功！訂單已即時同步送至 phpMyAdmin 資料庫。", ButtonType.OK);
            alert.setTitle("系統同步成功");
            alert.setHeaderText(null);
            alert.showAndWait();

            // 點完後清空購物車與總金額
            cartTable.getItems().clear();
            totalPrice = 0;
            totalLabel.setText("總計金額: $0");

        } catch (Exception ex) {
            try {
                if (conn != null) conn.rollback();
            } catch (Exception e) { e.printStackTrace(); }
            
            ex.printStackTrace();
            Alert alert = new Alert(Alert.AlertType.ERROR, "資料庫同步連線失敗，請確認 XAMPP 是否有開啟 MySQL！\n錯誤: " + ex.getMessage(), ButtonType.OK);
            alert.showAndWait();
        } finally {
            // 關閉並釋放資料庫連線資源
            try { if (psDetail != null) psDetail.close(); } catch (Exception e) {}
            try { if (psOrder != null) psOrder.close(); } catch (Exception e) {}
            try { if (conn != null) conn.close(); } catch (Exception e) {}
        }
    }

    public static void main(String[] args) {
        launch(args);
    }
}