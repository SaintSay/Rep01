<?php
session_start(); //Session start
function isAuth() {
    if (isset($_SESSION["is_auth"])) { //If session exist
        return $_SESSION["is_auth"]; //Returning the value of a session variable is_auth (stores true if authorized, false if not authorized)
    }
    else return false; //The user is not authorized because is_auth variable not created
}
if(isAuth()){
    echo "Привет ".$_SESSION["login"];
}
else{
    header("Location: /ldap.php");
  exit;
}
  echo "<br/><br/><a href='/ldap.php?is_exit=1'>Exit</a>"; //Show exit button

session_start();
echo session_id();

?>