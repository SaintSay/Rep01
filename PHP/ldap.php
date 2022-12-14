<?php
session_start();
header('Content-Type: text/html; charset=UTF-8');
mb_internal_encoding('UTF-8'); 
mb_http_output('UTF-8'); 
mb_http_input('UTF-8'); 

class AuthClass {
  /**
   * 
   * 
   * @return boolean 
   */
  public function isAuth() {
      if (isset($_SESSION["is_auth"])) { 
          return $_SESSION["is_auth"];
      }
      else return false;
  }
  
  /**
   * autorization
   * @param string $login
   * @param string $passwors 
   */
#if(isset($_POST["username"]) and isset($_POST["password"])){
#$user = htmlspecialchars($_POST["username"]);
#$password = htmlspecialchars($_POST["password"]);

  public function auth($login, $password) {
    $host = 'DC name';
    $domain = 'Domain';
    $basedn = 'DC=domain,DC=local';
    $group = 'Security group name';

    $ad = ldap_connect("ldap://{$host}.{$domain}") or die('Could not connect to LDAP server.');

    ldap_set_option($ad, LDAP_OPT_PROTOCOL_VERSION, 3);
    ldap_set_option($ad, LDAP_OPT_REFERRALS, 0);
     
if(@ldap_bind($ad, $login."@.$domain", $password))
{

    $userdn = getDN($ad, $login, $basedn);
    
    if (checkGroupEx($ad, $userdn, getDN($ad, $group, $basedn)))
    {
      $_SESSION["is_auth"] = true; 
      $_SESSION["login"] = $login; 
      return true;
    }
    else
    {
      $_SESSION["is_auth"] = false;
      return false;
    }
    ldap_unbind($ad);
    
      if ($login == $this->_login && $passwors == $this->_password) { 
          $_SESSION["is_auth"] = true; 
          $_SESSION["login"] = $login; 
          return true;
      }
      else {
          $_SESSION["is_auth"] = false;
          return false; 
      }
  }
}
  
  /**
   *
   */
  public function getLogin() {
      if ($this->isAuth()) { 
          return $_SESSION["login"]; 
      }
  }
  
  
  public function out() {
    $_SESSION = array();
    if (ini_get("session.use_cookies")) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000,
            $params["path"], $params["domain"],
            $params["secure"], $params["httponly"]
        );
    }
    
    session_destroy();
  }
}

$auth = new AuthClass();

if (isset($_POST["login"]) && isset($_POST["password"])) {
  if (!$auth->auth($_POST["login"], $_POST["password"])) {
      echo '<h2 style="color:red;">Login and password wrong!</h2>';
  }
}

if (isset($_GET["is_exit"])) {
  if ($_GET["is_exit"] == 1) {
      $auth->out();
      header("Location: ?is_exit=0"); 
  }
}
?>

<?php 
if ($auth->isAuth()) { 
  echo "Hello, " . $auth->getLogin() ;
 echo "<br/><br/><a href='/session.php'>Reference for session checkup</a>"; 
  echo "<br/><br/><a href='?is_exit=1'>Exit</a>";

header( "refresh:3;url=/index.php" );

} 
else {
?>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
    <title>AD</title>
    <link rel="stylesheet" href="http://maxcdn.bootstrapcdn.com/bootstrap/latest/css/bootstrap.css">
    <style>
	form {max-width: 300px;margin:auto}
	input {margin-bottom:10px}
    </style>
</head>
<body>
    <div class="container">
	<h1 class="text-center">Active Directory</h1>
	<form method="POST">
	    <input type="text" name="login" placeholder="login" class="form-control" required>
	    <input type="password" name="password" placeholder="password" class="form-control" required>
	    <input type="submit" class="btn btn-default btn-block" value="Enter">
	</form>
    </div>
</body>
</html>
<?php
}
?>

<?php


/**
 * This function searchs in LDAP tree entry specified by samaccountname and
 * returns its DN or epmty string on failure.
 *
 * @param resource $ad
 *          An LDAP link identifier, returned by ldap_connect().
 * @param string $samaccountname
 *          The sAMAccountName, logon name.
 * @param string $basedn
 *          The base DN for the directory.
 * @return string
 */
function getDN($ad, $samaccountname, $basedn)
{
  $result = ldap_search($ad, $basedn, "(samaccountname={$samaccountname})", array('dn'));
  if (! $result)
  {
    return '';
  }
 
  $entries = ldap_get_entries($ad, $result);
  if ($entries['count'] > 0)
  {
    return $entries[0]['dn'];
  }
 
  return '';
}
 
/**
 * This function retrieves and returns Common Name from a given Distinguished
 * Name.
 *
 * @param string $dn
 *          The Distinguished Name.
 * @return string The Common Name.
 */
function getCN($dn)
{
  preg_match('/[^,]*/', $dn, $matchs, PREG_OFFSET_CAPTURE, 3);
  return $matchs[0][0];
}
 
/**
 * This function checks group membership of the user, searching only in
 * specified group (not recursively).
 *
 * @param resource $ad
 *          An LDAP link identifier, returned by ldap_connect().
 * @param string $userdn
 *          The user Distinguished Name.
 * @param string $groupdn
 *          The group Distinguished Name.
 * @return boolean Return true if user is a member of group, and false if not
 *         a member.
 */
function checkGroup($ad, $userdn, $groupdn)
{
  $result = ldap_read($ad, $userdn, "(memberof={$groupdn})", array(
    'members'
  ));
  if (! $result)
  {
    return false;
  }
 
  $entries = ldap_get_entries($ad, $result);
 
  return ($entries['count'] > 0);
}
 
/**
 * This function checks group membership of the user, searching in specified
 * group and groups which is its members (recursively).
 *
 * @param resource $ad
 *          An LDAP link identifier, returned by ldap_connect().
 * @param string $userdn
 *          The user Distinguished Name.
 * @param string $groupdn
 *          The group Distinguished Name.
 * @return boolean Return true if user is a member of group, and false if not
 *         a member.
 */
function checkGroupEx($ad, $userdn, $groupdn)
{
  $result = ldap_read($ad, $userdn, '(objectclass=*)', array('memberof' ));
  if (! $result)
  {
    return false;
  }
 
  $entries = ldap_get_entries($ad, $result);
  if ($entries['count'] <= 0)
  {
    return false;
  }
 
  if (empty($entries[0]['memberof']))
  {
    return false;
  }
 
  for ($i = 0; $i < $entries[0]['memberof']['count']; $i ++)
  {
    if ($entries[0]['memberof'][$i] == $groupdn)
    {
      return true;
    }
    elseif (checkGroupEx($ad, $entries[0]['memberof'][$i], $groupdn))
    {
      return true;
    }
  }
 
  return false;
}
?>