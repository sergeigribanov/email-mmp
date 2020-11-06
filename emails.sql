create table if not exists tags (
id integer unique primary key,
tag varchar(30) unique not null);

create table if not exists groups (
id integer unique primary key,
group_number integer unique not null);

create table if not exists persons (
id integer unique primary key,
last_name varchar(100),
first_name varchar(100),
email varchar(100),
tag varchar(30) not null,
group_number integer not null,
io varchar(100) not null,
foreign key(tag) references tags(tag),
foreign key(group_number) references groups(group_number),
unique(tag, email),
unique(email, io),
unique(last_name, first_name, email, tag));

insert into tags (tag)
VALUES
("test"),
("exam");

insert into groups (group_number)
VALUES
(0),
(17341),
(17342),
(17344),
(17346),
(17347),
(17348),
(17349),
(17350),
(17351),
(17353),
(17355);

insert into persons (last_name, first_name, group_number, email, io, tag)
VALUES
("Иванов", "Иван", 0, "mailto:ivanov1@example.com,ivanov2@example.com",
	     	       "И.А.", "test");

insert into persons (last_name, first_name, group_number, email, io, tag)
VALUES
("Студент", "Петр", 17344, "mailto:p.student@g.nsu.ru,studen@example.com", "П.С.", "exam");
