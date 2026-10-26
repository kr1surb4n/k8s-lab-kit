# Proponuję Ci etapy do ogarnięcia

## 1. Na sucho – przestudiowanie 30% dokumentacji do Kubernetesów

https://kubernetes.io/docs/

- Nie wiem, jak się dobrać do dobrej wiedzy.
- Pytania:
  - Co to jest Pod?
  - Co to jest Service i jakie ma warianty?
  - Jakie są metody na udostępnienie usługi z Kubernetesów na zewnątrz (usługi HTTP – różne warianty, usługi TCP/IP)?
  - Co to jest Deployment?
  - Co to jest StatefulSet?
  - Czym różni się Deployment od StatefulSet? (dość trudne pytanie poza oczywistościami)
  - Jaki czas obowiązuje w Cron* i jak uruchamiać ręcznie zadania?

## 2. Na sucho – zarządzanie konfiguracjami (manifestami) na wielu środowiskach

a) Na sucho – przestudiowanie https://kustomize.io/

b) Na sucho – przestudiowanie https://helm.sh/

## 3. Pierwszy własny jednowęzłowy Kubernetes – k3s lub minikube

a) Uruchom Apache2 lub nginx serwujący jedną statyczną stronę.

- Udostępnij usługę poza klaster.

b) Uruchom Magento (z MySQL) z użyciem Helm Chartów.

## 4. Uruchom jednowęzłowo wszystkie małe implementacje Kubernetesów + Rancher

- k3s
- k0s
- minikube
- inne
- Rancher

## 5. Stwórz swój własny projekt w PHP + MySQL + Apache2 (revproxy) – wszystko w oddzielnych Podach

- Ma posiadać StatefulSet z MySQL (dowolnego wyboru źródło, użyj gotowców lub napisz swoje).
- Ma posiadać coś z PHP, np. Apache2 lub nginx, które wykona 1 SELECT z MySQL i pokaże wynik na stronie WWW.
- Dodaj reverse proxy na Apache2 (ma proxy'ować tylko jeden URL, który obsługuje ww. coś z PHP).
- Do wszystkiego miej manifesty (pliki z obiektami do Kubernetesów).
- Sam stwórz Dockerfile'e potrzebne do obrazów do powyższych (obowiązkowo do czegoś z PHP i reverse proxy na Apache2).
- Utwórz własne repozytorium obrazów.

## 6. Zapakuj pkt 5 w oddzielne Helm Charty

- Utwórz własne repozytorium Helm Chartów.
- Zapakuj kawałki z pkt 5 w oddzielne Helm Charty.
- Utwórz jednego Helm Charta, który korzysta z utworzonych Helm Chartów.
- Uruchom wszystko z Helm Chartów.

## 7. Utwórz swoje repozytorium Git (jako usługa po SSH) – w swoim systemie

- Uwierzytelnienie na jednego użytkownika po kluczach SSH.

## 8. Zapakuj pkt 5 w repozytorium z użyciem Kustomize

- Załóż, że mają być minimum 2 środowiska: dev i prod, pozwól na tworzenie większej liczby (przewidź to).
- Zapisz strukturę w swoim repozytorium.
- Uruchom wszystko na dwóch środowiskach z repo (dev i prod).

## 9. Uruchom Argo CD

a) Podepnij pkt 8 pod Argo CD – zmiana + push do Git ma dać efekt w uruchomionych obiektach Kubernetes (np. zmiana liczby instancji w coś z PHP w repo Git ma dać wynik w kubernetesach).

b) Podepnij pkt 6 pod Argo CD – niech Argo CD obsługuje Helm Charty (czy to z repozytorium Helm Chartów bezpośrednio, czy pośrednio).
