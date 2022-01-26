# How I tried to automate deleting layer versions (some time ago already) and still got to delete them manually.

layer=$1
region=$2

get_versions () {
  echo $(aws lambda list-layer-versions --layer-name "$layer" --region "$region" --output text --query LayerVersions[].Version | tr '[:blank:]' '\n')
}

versions=$(get_versions "$region")
for version in $versions;
do
  echo "deleting arn:aws:lambda:$region:*:layer:$layer:$version"
  aws lambda delete-layer-version --region "$region" --layer-name "$layer" --version "$version"
done
