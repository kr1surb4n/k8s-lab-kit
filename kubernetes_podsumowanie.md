# Kubernetes i Narzędzia Pokrewne – Podsumowanie Zagadnień

Niniejszy dokument zbiera i porządkuje zagadnienia techniczne, koncepcje oraz praktyczne podejścia do technologii Kubernetes, które były wcześniej omawiane.

## 1. Środowisko lokalne i alternatywne dystrybucje
- **Minikube:** Główne środowisko uruchomieniowe wykorzystywane do lokalnych testów, eksperymentów i nauki klastrów Kubernetes.
- **Lżejsze alternatywy serwerowe:** Rozważanie dystrybucji takich jak **K3s** oraz **MicroK8s** jako stabilnych, minimalistycznych środowisk produkcyjnych lub testowych do wdrożeń na własnym sprzęcie.

## 2. Pakiety i wdrożenia (Helm)
- **Helm Charts:** Wykorzystanie menedżera pakietów Helm do automatyzacji wdrożeń, zarządzania wersjami aplikacji oraz konfiguracji złożonych systemów w klastrze.
- Przykłady i testy wdrożeniowe obejmowały m.in. aplikacje takie jak **Nginx** oraz **Magento**.

## 3. Konfiguracja, sieć i dane
- **Udostępnianie usług (Services & Ingress):** Konfiguracja dostępu do aplikacji działających wewnątrz klastra z poziomu sieci zewnętrznej (poza klaster).
- **Zarządzanie wolumenami (Persistent Volumes / PVC):** Przypisywanie, mapowanie i utrwalanie danych dla kontenerów wymagających dysku.
- **Konfiguracja aplikacji:** Wykorzystanie obiektów **ConfigMap** oraz przekazywania zmiennych środowiskowych do kontenerów.

## 4. Podejście do nauki i rozwiązywania problemów
- **Praktyczny troubleshooting:** Stawianie na empiryczne rozwiązywanie realnych błędów, analizowanie logów i zachowania klastra bezpośrednio w praktyce.
- **Unikanie suchej teorii:** Nauka oparta na budowaniu i uruchamianiu rzeczywistych projektów zamiast biernego czytania oficjalnej dokumentacji.
