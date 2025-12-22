using System;

namespace RefactoringGuru.DesignPatterns.Bridge.ShapePainter
{
    class Shape
    {
        protected IPainter _painter;

        public Shape(IPainter painter)
        {
            this._painter = painter;
        }

        public virtual string Draw()
        {
            return "Shape: Base drawing with:\n" +
                _painter.Paint("Shape");
        }
    }

    class Circle : Shape
    {
        public Circle(IPainter painter) : base(painter)
        {
        }

        public override string Draw()
        {
            return "Circle drawing with:\n" +
                _painter.Paint("Circle");
        }
    }

    class Rectangle : Shape
    {
        public Rectangle(IPainter painter) : base(painter)
        {
        }

        public override string Draw()
        {
            return "Rectangle drawing with:\n" +
                _painter.Paint("Rectangle");
        }
    }

    public interface IPainter
    {
        string Paint(string shapeName);
    }

    class RedPainter : IPainter
    {
        public string Paint(string shapeName)
        {
            return $"Painting {shapeName} in Red\n";
        }
    }

    class BluePainter : IPainter
    {
        public string Paint(string shapeName)
        {
            return $"Painting {shapeName} in Blue\n";
        }
    }

    class Client
    {
        public void ClientCode(Shape shape)
        {
            Console.Write(shape.Draw());
        }
    }

    class Program
    {
        static void Main(string[] args)
        {
            Client client = new Client();

            Shape shape;

            shape = new Circle(new RedPainter());
            client.ClientCode(shape);

            Console.WriteLine();

            shape = new Rectangle(new BluePainter());
            client.ClientCode(shape);
        }
    }
}
