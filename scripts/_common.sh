#!/bin/bash
set -eu
source /usr/share/yunohost/helpers

package_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/.."
  pwd
}
