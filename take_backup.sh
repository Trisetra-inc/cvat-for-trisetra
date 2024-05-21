docker compose stop
mkdir -p backup
docker run --rm --name temp_backup --volumes-from cvat_db -v $(pwd)/backup:/backup ubuntu tar -czvf /backup/cvat_db.tar.gz /var/lib/postgresql/data
docker run --rm --name temp_backup --volumes-from cvat_server -v $(pwd)/backup:/backup ubuntu tar -czvf /backup/cvat_data.tar.gz /home/django/data
# [optional]
# docker run --rm --name temp_backup --volumes-from cvat_elasticsearch -v $(pwd)/backup:/backup ubuntu tar -czvf /backup/cvat_events.tar.gz /usr/share/elasticsearch/data
echo "Backup created successfully:"
ls -lH backup
