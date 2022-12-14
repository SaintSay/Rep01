src=/wildcard
dst=/etc/nginx/certs/default
 
chown -R root:root $src/
 
if cmp -s $src/cert.pem $dst/cert.pem
then :
else cp -f $src/cert.pem $dst/cert.pem
cp -f $src/chain.pem $dst/chain.pem
cp -f $src/privkey.pem $dst/privkey.pem
openssl x509 -in $dst/cert.pem -noout
service nginx restart
service httpd restart
fi
rm -r $src/*