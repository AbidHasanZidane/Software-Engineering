<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {
      width: 300px;
      padding: 10px;
      font-family: Arial, sans-serif;
    }
    #result {
      margin-top: 10px;
      padding: 8px;
      border-radius: 4px;
      background: #f5f5f5;
      min-height: 60px;
    }
    .loading {
      color: #666;
      font-style: italic;
    }
    .error {
      color: red;
    }
    .success {
      color: green;
    }
    button {
      width: 100%;
      padding: 8px;
      background: #007bff;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }
    button:hover {
      background: #0056b3;
    }
  </style>
</head>
<body>
  <h3>Fake News Detector</h3>
  <div id="selectedText">No text selected</div>
  <button id="checkBtn">Check Selected Text</button>
  <div id="result">Result will appear here</div>
  <script src="popup.js"></script>
</body>
</html>
