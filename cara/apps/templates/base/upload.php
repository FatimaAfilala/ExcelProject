<?php
if(!empty($_POST['data'])){
    $data = base64_decode($_POST['data']);
   
    $fileName = $_POST['filename'];
   
    file_put_contents( "uploads/".$fileName.".pdf", $data );
    } else {
    echo "No Data Sent";
    }
    exit();
?>